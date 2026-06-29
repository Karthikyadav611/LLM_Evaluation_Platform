import argparse
import hashlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.comparison import compare_metrics, compare_test_results
from app.config import Settings
from app.dataset_loader import load_golden_dataset
from app.evaluation_runner import evaluate_prompt_version
from app.evaluators import Evaluator
from app.judge import LLMJudge
from app.metrics import calculate_summary
from app.pricing import PricingCatalog
from app.prompt_manager import PromptManager
from app.providers.factory import create_provider
from app.quality_gate import determine_pipeline_status, run_quality_gates, run_validity_checks
from app.report_generator import export_reports
from app.security import sanitize_text
from app.services.persistence_service import persist_prompt_comparison_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run baseline and candidate LLM prompt evaluation.")
    parser.add_argument("--test-limit", type=int, default=None)
    parser.add_argument("--no-delay", action="store_true", help="Disable configured delay between requests.")
    parser.add_argument("--generation-provider", default=None)
    parser.add_argument("--generation-model", default=None)
    parser.add_argument("--judge-provider", default=None)
    parser.add_argument("--judge-model", default=None)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "data" / "golden_dataset.json",
        help="Path to the golden dataset JSON file.",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=PROJECT_ROOT / "reports",
        help="Directory where report artifacts will be written.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings()
    generation_provider = (getattr(args, "generation_provider", None) or settings.generation_provider).lower()
    judge_provider = (getattr(args, "judge_provider", None) or settings.judge_provider).lower()
    generation_model = getattr(args, "generation_model", None) or settings.generation_model
    judge_model = getattr(args, "judge_model", None) or settings.judge_model

    try:
        generation_api_key = settings.require_api_key(generation_provider)
        judge_api_key = settings.require_api_key(judge_provider)
    except ValueError as exc:
        print(f"Pipeline status: ERROR\n{sanitize_text(exc)}")
        return 2

    try:
        pricing = PricingCatalog.from_file(Path(settings.pricing_config_path) if settings.pricing_config_path else None)
        gen_client = create_provider(
            generation_provider,
            api_key=generation_api_key,
            model=generation_model,
            pricing_catalog=pricing,
            max_retries=settings.max_retries,
        )
        gen_client.default_temperature = settings.temperature
        gen_client.default_max_output_tokens = settings.max_output_tokens
        judge_client = create_provider(
            judge_provider,
            api_key=judge_api_key,
            model=judge_model,
            pricing_catalog=pricing,
            max_retries=settings.max_retries,
        )
        judge_client.default_temperature = 0.0
        judge_client.default_max_output_tokens = settings.max_output_tokens
    except Exception as exc:
        print(f"Pipeline status: ERROR\nFailed to initialize LLM client: {sanitize_text(exc)}")
        return 2

    connection_ok, connection_error = gen_client.check_connection()
    if not connection_ok:
        print(f"Pipeline status: ERROR\nFailed to connect to LLM provider: {connection_error}")
        return 2

    limit = args.test_limit if args.test_limit is not None else settings.test_limit
    delay = 0.0 if args.no_delay else settings.request_delay_seconds
    dataset_path = args.dataset if args.dataset.is_absolute() else PROJECT_ROOT / args.dataset
    reports_dir = args.reports_dir if args.reports_dir.is_absolute() else PROJECT_ROOT / args.reports_dir

    prompt_manager = PromptManager(PROJECT_ROOT)
    try:
        test_cases = load_golden_dataset(dataset_path, limit=limit)
    except Exception as exc:
        print(f"Pipeline status: ERROR\nDataset validation failed: {exc}")
        return 2
    evaluator = Evaluator()
    judge = LLMJudge(judge_client, prompt_manager.get_judge_prompt())
    quality_thresholds = {
        "correctness": settings.minimum_correctness,
        "relevancy": settings.minimum_relevancy,
        "faithfulness": settings.minimum_faithfulness,
    }
    dataset_hash = hashlib.sha256(dataset_path.read_bytes()).hexdigest()

    baseline_results = evaluate_prompt_version(
        "Baseline",
        prompt_manager.get_baseline_prompt(),
        test_cases,
        gen_client,
        judge,
        evaluator,
        delay,
        quality_thresholds=quality_thresholds,
    )
    candidate_results = evaluate_prompt_version(
        "Candidate",
        prompt_manager.get_candidate_prompt(),
        test_cases,
        gen_client,
        judge,
        evaluator,
        delay,
        quality_thresholds=quality_thresholds,
    )
    for result in baseline_results + candidate_results:
        result.dataset_name = dataset_path.name
        result.dataset_hash = dataset_hash
        result.judge_provider = judge_provider
        result.judge_model = judge_model

    baseline_metrics = calculate_summary(baseline_results)
    candidate_metrics = calculate_summary(candidate_results)
    prompt_comparison = compare_metrics(
        baseline_metrics,
        candidate_metrics,
        settings.minimum_valid_evaluation_ratio,
    )
    test_level_comparison = compare_test_results(baseline_results, candidate_results)

    validity_checks = run_validity_checks(candidate_metrics, settings, connection_ok, connection_error)
    quality_gates = run_quality_gates(candidate_metrics, settings)
    status = determine_pipeline_status(validity_checks, quality_gates)

    settings.generation_provider = generation_provider
    settings.generation_model = generation_model
    settings.judge_provider = judge_provider
    settings.judge_model = judge_model
    report_result = export_reports(
        reports_dir,
        baseline_results,
        candidate_results,
        baseline_metrics,
        candidate_metrics,
        prompt_comparison,
        test_level_comparison,
        validity_checks,
        quality_gates,
        settings,
        status,
    )
    persistence_warning = persist_prompt_comparison_run(
        settings=settings,
        report_result=report_result,
        baseline_results=baseline_results,
        candidate_results=candidate_results,
        baseline_metrics=baseline_metrics,
        candidate_metrics=candidate_metrics,
        quality_gates=[*validity_checks, *quality_gates],
        dataset_path=dataset_path,
        baseline_prompt=prompt_manager.get_baseline_prompt(),
        candidate_prompt=prompt_manager.get_candidate_prompt(),
    )

    print(f"\nExperiment ID: {report_result.experiment_id}")
    print(f"Pipeline status: {status}")
    print(f"Reports saved to: {report_result.report_directory}")
    if persistence_warning:
        print(f"Persistence warning: {persistence_warning}")
    print(
        "Candidate summary: "
        f"{candidate_metrics.passed_tests}/{candidate_metrics.total_tests} passed, "
        f"{candidate_metrics.error_tests} errors, "
        f"valid ratio {candidate_metrics.valid_evaluation_ratio}"
    )
    return 0 if status == "PASS" else 1 if status == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())

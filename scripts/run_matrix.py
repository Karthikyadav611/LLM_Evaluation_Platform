import argparse
import hashlib
import json
import sys
import uuid
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import Settings
from app.datasets.loader import load_dataset
from app.experiments.matrix_runner import expand_prompt_model_matrix
from app.experiments.runner import ExperimentRunner
from app.experiments.summaries import summarize_by_configuration
from app.judge import LLMJudge
from app.pricing import PricingCatalog
from app.prompts.loader import load_prompt_file
from app.providers.factory import create_provider
from app.quality_gate import determine_pipeline_status, run_quality_gates, run_validity_checks
from app.report_generator import _results_to_dataframe
from app.security import sanitize_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run prompt-model matrix LLM evaluations.")
    parser.add_argument("--config", type=Path, required=True, help="Path to experiment YAML.")
    parser.add_argument("--reports-dir", type=Path, default=PROJECT_ROOT / "reports")
    parser.add_argument("--test-limit", type=int, default=None)
    parser.add_argument("--no-delay", action="store_true", help="Accepted for CLI compatibility.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings()
    config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    reports_dir = args.reports_dir if args.reports_dir.is_absolute() else PROJECT_ROOT / args.reports_dir

    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        dataset_path = Path(config.get("dataset", "data/golden_dataset.json"))
        dataset_path = dataset_path if dataset_path.is_absolute() else PROJECT_ROOT / dataset_path
        test_cases = load_dataset(dataset_path, limit=args.test_limit or config.get("test_limit"))
        prompts = _load_prompt_config(config.get("prompts") or {})
        provider_models = [
            (str(item["provider"]).lower(), str(item["model"]))
            for item in config.get("models", [])
        ]
        if not prompts or not provider_models:
            raise ValueError("Matrix config requires prompts and models")
        judge_config = config.get("judge", {})
        judge_provider = str(judge_config.get("provider", settings.judge_provider)).lower()
        judge_model = str(judge_config.get("model", settings.judge_model))
        judge_prompt = load_prompt_file(PROJECT_ROOT / "prompts" / "judge_prompt.txt")
    except Exception as exc:
        print(f"Pipeline status: ERROR\nInvalid matrix config: {exc}")
        return 2

    experiment_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    dataset_hash = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    configurations = expand_prompt_model_matrix(
        experiment_id=experiment_id,
        run_id=run_id,
        prompts=prompts,
        provider_models=provider_models,
        judge_provider=judge_provider,
        judge_model=judge_model,
        dataset_name=dataset_path.name,
        dataset_hash=dataset_hash,
        temperature=float(config.get("temperature", settings.temperature)),
        max_output_tokens=int(config.get("max_output_tokens", settings.max_output_tokens)),
    )

    pricing = PricingCatalog.from_file(Path(settings.pricing_config_path) if settings.pricing_config_path else None)
    all_results = []
    status = "PASS"
    try:
        judge_key = settings.require_api_key(judge_provider)
        judge_provider_client = create_provider(
            judge_provider,
            api_key=judge_key,
            model=judge_model,
            pricing_catalog=pricing,
            max_retries=settings.max_retries,
        )
        judge = LLMJudge(judge_provider_client, judge_prompt)
        for configuration in configurations:
            generator_key = settings.require_api_key(configuration.provider)
            generator = create_provider(
                configuration.provider,
                api_key=generator_key,
                model=configuration.model,
                pricing_catalog=pricing,
                max_retries=settings.max_retries,
            )
            runner = ExperimentRunner(
                generator=generator,
                judge=judge,
                max_concurrent_requests=settings.max_concurrent_requests,
                quality_thresholds={
                    "correctness": settings.minimum_correctness,
                    "relevancy": settings.minimum_relevancy,
                    "faithfulness": settings.minimum_faithfulness,
                },
            )
            all_results.extend(runner.run_configuration(configuration, test_cases))
    except Exception as exc:
        print(f"Pipeline status: ERROR\n{sanitize_text(exc)}")
        return 2

    reports_dir.mkdir(parents=True, exist_ok=True)
    results_df = _results_to_dataframe(all_results)
    results_df.to_csv(reports_dir / "test_results.csv", index=False)
    summaries = summarize_by_configuration(all_results)
    configuration_rows = [
        {"configuration_id": configuration_id, **summary.model_dump()}
        for configuration_id, summary in summaries.items()
    ]
    import pandas as pd

    pd.DataFrame(configuration_rows).to_csv(reports_dir / "configuration_results.csv", index=False)
    pd.DataFrame(configuration_rows).to_csv(reports_dir / "model_comparison.csv", index=False)

    gate_rows: list[dict] = []
    for configuration_id, summary in summaries.items():
        validity = run_validity_checks(summary, settings, True)
        quality = run_quality_gates(summary, settings)
        configuration_status = determine_pipeline_status(validity, quality)
        if configuration_status == "ERROR":
            status = "ERROR"
        elif configuration_status == "FAIL" and status != "ERROR":
            status = "FAIL"
        gate_rows.extend(
            {"configuration_id": configuration_id, "gate_type": "validity", **gate.model_dump()}
            for gate in validity
        )
        gate_rows.extend(
            {"configuration_id": configuration_id, "gate_type": "quality", **gate.model_dump()}
            for gate in quality
        )
    pd.DataFrame(gate_rows).to_csv(reports_dir / "quality_gates.csv", index=False)
    (reports_dir / "experiment_summary.json").write_text(
        json.dumps(
            {
                "experiment_id": experiment_id,
                "run_id": run_id,
                "mode": "matrix",
                "pipeline_status": status,
                "dataset_name": dataset_path.name,
                "dataset_hash": dataset_hash,
                "configuration_count": len(configurations),
                "comparison_fairness": {
                    "same_dataset": True,
                    "same_temperature": True,
                    "same_max_output_tokens": True,
                    "same_judge": True,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Pipeline status: {status}")
    print(f"Reports written to: {reports_dir}")
    return 0 if status == "PASS" else 1 if status == "FAIL" else 2


def _load_prompt_config(prompt_config: dict) -> dict[str, str]:
    prompts = {}
    for name, value in prompt_config.items():
        if isinstance(value, dict) and "path" in value:
            path = Path(value["path"])
            path = path if path.is_absolute() else PROJECT_ROOT / path
            prompts[str(name)] = load_prompt_file(path)
        else:
            prompts[str(name)] = str(value)
    return prompts


if __name__ == "__main__":
    raise SystemExit(main())

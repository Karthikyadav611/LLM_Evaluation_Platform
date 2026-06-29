import hashlib
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
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
from app.report_generator import build_reports_zip_from_files, export_reports
from app.security import sanitize_text
from app.services.persistence_service import persist_prompt_comparison_run
from dashboard.helpers import api_call_estimate
from dashboard.state import set_active_results, set_session_api_key

REPORTS_DIR = PROJECT_ROOT / "reports"


def main() -> None:
    st.set_page_config(page_title="Run Evaluation", layout="wide")
    st.title("Run Evaluation")
    st.info("Your API keys are used only during this evaluation session and are not intentionally stored.")

    settings = Settings()
    mode_label = st.selectbox(
        "Evaluation Mode",
        ["Prompt comparison", "Model comparison", "Prompt-model matrix"],
    )
    mode = {
        "Prompt comparison": "prompt_comparison",
        "Model comparison": "model_comparison",
        "Prompt-model matrix": "matrix",
    }[mode_label]

    gen_col, judge_col = st.columns(2)
    with gen_col:
        generation_provider = st.selectbox(
            "Generation provider",
            ["groq", "gemini", "openai", "anthropic"],
            index=["groq", "gemini", "openai", "anthropic"].index(settings.generation_provider),
        )
        generation_key = st.text_input("Generation API key", type="password")
        set_session_api_key(generation_provider, generation_key)
        generation_model = st.text_input("Generation model", value=settings.generation_model)
        if st.button("Fetch generation models"):
            _fetch_models(generation_provider, generation_key, generation_model)

    with judge_col:
        judge_provider = st.selectbox(
            "Judge provider",
            ["groq", "gemini", "openai", "anthropic"],
            index=["groq", "gemini", "openai", "anthropic"].index(settings.judge_provider),
        )
        judge_key = st.text_input("Judge API key", type="password")
        set_session_api_key(judge_provider, judge_key)
        judge_model = st.text_input("Judge model", value=settings.judge_model)
        if st.button("Fetch judge models"):
            _fetch_models(judge_provider, judge_key, judge_model)

    if generation_provider == judge_provider and generation_model == judge_model:
        st.warning("The generator and judge are identical. This may introduce self-evaluation bias.")

    prompt_manager = PromptManager(PROJECT_ROOT)
    baseline_prompt = st.text_area("Baseline prompt", value=prompt_manager.get_baseline_prompt(), height=140)
    candidate_prompt = st.text_area("Candidate prompt", value=prompt_manager.get_candidate_prompt(), height=180)
    model_matrix = st.text_area(
        "Model entries for model comparison or matrix",
        value=f"{generation_provider}:{generation_model}",
        help="Use one provider:model per line. Prompt comparison uses the generation provider/model fields.",
    )

    dataset_path = PROJECT_ROOT / "data" / "golden_dataset.json"
    test_limit = st.number_input("Test limit", min_value=1, value=settings.test_limit or 3, step=1)
    test_cases = load_golden_dataset(dataset_path, limit=int(test_limit))
    st.caption(f"Dataset: {dataset_path.name} | Loaded tests: {len(test_cases)}")

    threshold_cols = st.columns(4)
    minimum_correctness = threshold_cols[0].number_input("Minimum correctness", 0.0, 1.0, settings.minimum_correctness)
    minimum_relevancy = threshold_cols[1].number_input("Minimum relevancy", 0.0, 1.0, settings.minimum_relevancy)
    minimum_faithfulness = threshold_cols[2].number_input("Minimum faithfulness", 0.0, 1.0, settings.minimum_faithfulness)
    minimum_pass_rate = threshold_cols[3].number_input("Minimum pass rate", 0.0, 1.0, settings.minimum_pass_rate)
    settings.minimum_correctness = minimum_correctness
    settings.minimum_relevancy = minimum_relevancy
    settings.minimum_faithfulness = minimum_faithfulness
    settings.minimum_pass_rate = minimum_pass_rate

    model_count = max(1, len(_parse_model_entries(model_matrix)))
    prompt_count = 2 if mode in {"prompt_comparison", "matrix"} else 1
    estimate = api_call_estimate(mode, len(test_cases), prompt_count, model_count)
    st.metric("Approximate API calls", estimate["approximate_total"])
    st.caption("Retries may increase this count.")
    quota_ok = st.checkbox("I understand this evaluation will use my API quota.")

    if st.button("Test connections"):
        _test_connections(settings, generation_provider, generation_key, generation_model, judge_provider, judge_key, judge_model)

    if st.button("Run Evaluation", type="primary", disabled=not quota_ok):
        if not generation_key or not judge_key:
            st.error("Enter temporary API keys for both generator and judge.")
            return
        with st.status("Running evaluation...", expanded=True):
            run_result = _run_prompt_comparison(
                settings=settings,
                generation_provider=generation_provider,
                generation_key=generation_key,
                generation_model=generation_model,
                judge_provider=judge_provider,
                judge_key=judge_key,
                judge_model=judge_model,
                baseline_prompt=baseline_prompt,
                candidate_prompt=candidate_prompt,
                test_cases=test_cases,
                dataset_path=dataset_path,
            )
        st.success(f"Evaluation completed with status {run_result['status']}")
        st.write(f"Reports saved to: {run_result['report_directory']}")
        if run_result.get("persistence_warning"):
            st.warning(f"Reports were saved, but SQLite persistence failed: {run_result['persistence_warning']}")
        st.cache_data.clear()
        zip_buffer = build_reports_zip_from_files(run_result["files"])
        st.download_button(
            "Download report ZIP",
            data=zip_buffer,
            file_name="evaluation_reports.zip",
            mime="application/zip",
        )


def _fetch_models(provider: str, api_key: str, model: str) -> None:
    if not api_key:
        st.warning("Enter an API key before fetching models.")
        return
    try:
        client = create_provider(provider, api_key=api_key, model=model)
        models = client.list_models()
        if models:
            st.dataframe({"model": models}, use_container_width=True)
        else:
            st.info("Could not fetch models. Enter a model name manually.")
    except Exception as exc:
        st.info(f"Could not fetch models. Enter a model name manually. {sanitize_text(exc)}")


def _test_connections(settings: Settings, gen_provider: str, gen_key: str, gen_model: str, judge_provider: str, judge_key: str, judge_model: str) -> None:
    for label, provider, api_key, model in [
        ("Generator", gen_provider, gen_key, gen_model),
        ("Judge", judge_provider, judge_key, judge_model),
    ]:
        try:
            client = create_provider(provider, api_key=api_key, model=model, max_retries=settings.max_retries)
            ok, message = client.test_connection()
            st.write(f"{label}: {'OK' if ok else 'ERROR'} - {sanitize_text(message)}")
        except Exception as exc:
            st.write(f"{label}: ERROR - {sanitize_text(exc)}")


def _run_prompt_comparison(
    *,
    settings: Settings,
    generation_provider: str,
    generation_key: str,
    generation_model: str,
    judge_provider: str,
    judge_key: str,
    judge_model: str,
    baseline_prompt: str,
    candidate_prompt: str,
    test_cases,
    dataset_path: Path,
) -> dict:
    pricing = PricingCatalog.from_file(Path(settings.pricing_config_path) if settings.pricing_config_path else None)
    generator = create_provider(
        generation_provider,
        api_key=generation_key,
        model=generation_model,
        pricing_catalog=pricing,
        max_retries=settings.max_retries,
    )
    generator.default_temperature = settings.temperature
    generator.default_max_output_tokens = settings.max_output_tokens
    judge_client = create_provider(
        judge_provider,
        api_key=judge_key,
        model=judge_model,
        pricing_catalog=pricing,
        max_retries=settings.max_retries,
    )
    judge_client.default_temperature = 0.0
    judge_client.default_max_output_tokens = settings.max_output_tokens
    judge = LLMJudge(judge_client, PromptManager(PROJECT_ROOT).get_judge_prompt())
    evaluator = Evaluator()
    quality_thresholds = {
        "correctness": settings.minimum_correctness,
        "relevancy": settings.minimum_relevancy,
        "faithfulness": settings.minimum_faithfulness,
    }
    baseline_results = evaluate_prompt_version(
        "Baseline",
        baseline_prompt,
        test_cases,
        generator,
        judge,
        evaluator,
        delay=0,
        quality_thresholds=quality_thresholds,
    )
    candidate_results = evaluate_prompt_version(
        "Candidate",
        candidate_prompt,
        test_cases,
        generator,
        judge,
        evaluator,
        delay=0,
        quality_thresholds=quality_thresholds,
    )
    dataset_hash = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    for result in baseline_results + candidate_results:
        result.dataset_name = dataset_path.name
        result.dataset_hash = dataset_hash
        result.provider = generation_provider
        result.model = generation_model
        result.judge_provider = judge_provider
        result.judge_model = judge_model

    baseline_metrics = calculate_summary(baseline_results)
    candidate_metrics = calculate_summary(candidate_results)
    prompt_comparison = compare_metrics(baseline_metrics, candidate_metrics)
    test_level_comparison = compare_test_results(baseline_results, candidate_results)
    validity = run_validity_checks(candidate_metrics, settings, True)
    quality = run_quality_gates(candidate_metrics, settings)
    status = determine_pipeline_status(validity, quality)
    settings.generation_provider = generation_provider
    settings.generation_model = generation_model
    settings.judge_provider = judge_provider
    settings.judge_model = judge_model
    report_result = export_reports(
        REPORTS_DIR,
        baseline_results,
        candidate_results,
        baseline_metrics,
        candidate_metrics,
        prompt_comparison,
        test_level_comparison,
        validity,
        quality,
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
        quality_gates=[*validity, *quality],
        dataset_path=dataset_path,
        baseline_prompt=baseline_prompt,
        candidate_prompt=candidate_prompt,
    )
    set_active_results({"baseline": baseline_results, "candidate": candidate_results})
    return {
        "status": status,
        "experiment_id": report_result.experiment_id,
        "report_directory": report_result.report_directory,
        "files": report_result.files,
        "persistence_warning": persistence_warning,
    }


def _parse_model_entries(text: str) -> list[tuple[str, str]]:
    entries = []
    for line in text.splitlines():
        if ":" in line:
            provider, model = line.split(":", 1)
            entries.append((provider.strip().lower(), model.strip()))
    return entries


if __name__ == "__main__":
    main()

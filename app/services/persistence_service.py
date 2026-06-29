import hashlib
from datetime import datetime
from pathlib import Path
from typing import Literal

from app.prompts.versioning import hash_prompt
from app.report_generator import ReportExportResult
from app.schemas import (
    EvaluationResult,
    ExperimentConfiguration,
    ExperimentSummary,
    QualityGateResult,
    VersionSummary,
)
from app.security import sanitize_text
from app.storage.database import create_database_engine, create_session_factory
from app.storage.migrations import initialize_database
from app.storage.repositories import ExperimentRepository


def persist_prompt_comparison_run(
    *,
    settings,
    report_result: ReportExportResult,
    baseline_results: list[EvaluationResult],
    candidate_results: list[EvaluationResult],
    baseline_metrics: VersionSummary,
    candidate_metrics: VersionSummary,
    quality_gates: list[QualityGateResult],
    dataset_path: Path,
    baseline_prompt: str,
    candidate_prompt: str,
    mode: Literal["prompt_comparison", "model_comparison", "matrix"] = "prompt_comparison",
) -> str | None:
    try:
        engine = create_database_engine(settings.database_url)
        initialize_database(engine)
        repository = ExperimentRepository(create_session_factory(engine))
        dataset_hash = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
        summary = ExperimentSummary(
            experiment_id=report_result.experiment_id,
            run_id=report_result.run_id,
            mode=mode,
            dataset_name=dataset_path.name,
            dataset_hash=dataset_hash,
            started_at=datetime.now().astimezone().isoformat(),
            completed_at=datetime.now().astimezone().isoformat(),
            status=report_result.pipeline_report.pipeline_status,
            configurations=[
                _configuration(
                    report_result,
                    "baseline",
                    "Baseline",
                    baseline_prompt,
                    baseline_results,
                    dataset_path.name,
                    dataset_hash,
                ),
                _configuration(
                    report_result,
                    "candidate",
                    "Candidate",
                    candidate_prompt,
                    candidate_results,
                    dataset_path.name,
                    dataset_hash,
                ),
            ],
        )
        repository.save_completed_run(
            summary=summary,
            results=[*baseline_results, *candidate_results],
            metric_summaries={"baseline": baseline_metrics, "candidate": candidate_metrics},
            quality_gates=quality_gates,
            report_directory=report_result.report_directory,
            report_files=sorted(report_result.files),
        )
    except Exception as exc:
        return sanitize_text(exc)
    return None


def _configuration(
    report_result: ReportExportResult,
    configuration_id: str,
    prompt_name: str,
    prompt_text: str,
    results: list[EvaluationResult],
    dataset_name: str,
    dataset_hash: str,
) -> ExperimentConfiguration:
    first = results[0] if results else None
    status: Literal["PENDING", "RUNNING", "PASS", "FAIL", "ERROR"] = "ERROR"
    if results and all(result.final_result == "PASS" for result in results):
        status = "PASS"
    elif results and any(result.final_result == "FAIL" for result in results):
        status = "FAIL"
    return ExperimentConfiguration(
        experiment_id=report_result.experiment_id,
        run_id=report_result.run_id,
        configuration_id=configuration_id,
        prompt_name=prompt_name,
        prompt_text=prompt_text,
        prompt_hash=hash_prompt(prompt_text),
        provider=first.provider if first and first.provider else "",
        model=first.model if first and first.model else "",
        judge_provider=first.judge_provider if first and first.judge_provider else "",
        judge_model=first.judge_model if first and first.judge_model else "",
        dataset_name=dataset_name,
        dataset_hash=dataset_hash,
        status=status,
    )

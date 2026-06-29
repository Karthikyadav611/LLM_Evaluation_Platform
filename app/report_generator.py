import io
import json
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel

from app.reports.persistence import prepare_experiment_directory, write_experiment_files
from app.schemas import EvaluationResult, PipelineReport, QualityGateResult, VersionSummary


@dataclass(frozen=True)
class ReportExportResult:
    pipeline_report: PipelineReport
    experiment_id: str
    run_id: str
    report_directory: str
    absolute_report_directory: Path
    files: dict[str, str | bytes]


def export_reports(
    reports_dir: Path,
    baseline_results: list[EvaluationResult],
    candidate_results: list[EvaluationResult],
    baseline_metrics: VersionSummary,
    candidate_metrics: VersionSummary,
    prompt_comparison: list[dict[str, Any]],
    test_level_comparison: list[dict[str, Any]],
    validity: list[QualityGateResult],
    quality: list[QualityGateResult],
    settings,
    pipeline_status: Literal["PASS", "FAIL", "ERROR"],
) -> ReportExportResult:
    requested_experiment_id = getattr(settings, "experiment_id", None) or f"exp-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    prepared = prepare_experiment_directory(reports_dir, requested_experiment_id)
    experiment_id = prepared.experiment_id
    run_id = getattr(settings, "run_id", None) or f"run-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    created_at = datetime.now().astimezone().isoformat()

    _annotate_prompt_comparison_results(
        baseline_results,
        candidate_results,
        experiment_id=experiment_id,
        run_id=run_id,
        settings=settings,
    )

    baseline_df = _results_to_dataframe(baseline_results)
    candidate_df = _results_to_dataframe(candidate_results)
    files: dict[str, str | bytes] = {}
    files["baseline_evaluation_results.csv"] = _df_to_csv(baseline_df)
    files["candidate_evaluation_results.csv"] = _df_to_csv(candidate_df)

    failed_candidate_df = candidate_df[candidate_df["final_result"] != "PASS"]
    files["failed_candidate_tests.csv"] = _df_to_csv(failed_candidate_df)

    files["prompt_comparison.csv"] = _df_to_csv(pd.DataFrame(prompt_comparison))
    files["test_level_comparison.csv"] = _df_to_csv(pd.DataFrame(test_level_comparison))
    all_results_df = pd.concat([baseline_df, candidate_df], ignore_index=True)
    files["test_results.csv"] = _df_to_csv(all_results_df)

    failed_candidate_ids = [
        result.id for result in candidate_results if result.final_result != "PASS"
    ]
    fixed_test_ids = [
        row["id"] for row in test_level_comparison if row.get("status") == "FIXED"
    ]
    regressed_test_ids = [
        row["id"] for row in test_level_comparison if row.get("status") == "REGRESSED"
    ]
    failed_df = all_results_df[all_results_df["final_result"] != "PASS"]
    files["failed_tests.csv"] = _df_to_csv(failed_df)
    files["fixed_tests.csv"] = _df_to_csv(pd.DataFrame({"id": fixed_test_ids}))
    files["regressed_tests.csv"] = _df_to_csv(pd.DataFrame({"id": regressed_test_ids}))

    configuration_rows = [
        _configuration_row("baseline", "Baseline", baseline_results, baseline_metrics),
        _configuration_row("candidate", "Candidate", candidate_results, candidate_metrics),
    ]
    files["configuration_results.csv"] = _df_to_csv(pd.DataFrame(configuration_rows))
    files["model_comparison.csv"] = _df_to_csv(pd.DataFrame(configuration_rows))
    files["quality_gates.csv"] = _df_to_csv(
        pd.DataFrame(
        [
            {"gate_type": "validity", **_to_jsonable(gate)}
            for gate in validity
        ]
        + [
            {"gate_type": "quality", **_to_jsonable(gate)}
            for gate in quality
        ]
        )
    )

    summary = PipelineReport(
        generation_provider=settings.generation_provider,
        generation_model=settings.generation_model,
        judge_provider=settings.judge_provider,
        judge_model=settings.judge_model,
        timestamp=created_at,
        thresholds=settings.thresholds(),
        validity_checks=validity,
        quality_gates=quality,
        baseline_metrics=baseline_metrics,
        candidate_metrics=candidate_metrics,
        pipeline_status=pipeline_status,
        failed_candidate_ids=failed_candidate_ids,
        fixed_test_ids=fixed_test_ids,
        regressed_test_ids=regressed_test_ids,
    )
    summary_payload = _to_jsonable(summary)
    summary_payload.update(
        {
            "experiment_id": experiment_id,
            "run_id": run_id,
            "status": pipeline_status,
            "created_at": created_at,
            "report_directory": prepared.relative_report_directory,
            "comparison_fairness": {
                "same_dataset": True,
                "same_temperature": True,
                "same_max_output_tokens": True,
                "same_judge": settings.judge_provider == settings.judge_provider
                and settings.judge_model == settings.judge_model,
                "warning": None,
            },
            "report_files": [
                "experiment_summary.json",
                "configuration_results.csv",
                "test_results.csv",
                "model_comparison.csv",
                "prompt_comparison.csv",
                "quality_gates.csv",
                "failed_tests.csv",
                "regressed_tests.csv",
                "fixed_tests.csv",
                "baseline_evaluation_results.csv",
                "candidate_evaluation_results.csv",
                "test_level_comparison.csv",
                "failed_candidate_tests.csv",
            ],
        }
    )

    summary_json = json.dumps(summary_payload, indent=2)
    files["evaluation_summary.json"] = summary_json
    files["experiment_summary.json"] = summary_json
    write_experiment_files(
        prepared,
        files,
        run_id=run_id,
        status=pipeline_status,
        created_at=created_at,
    )
    return ReportExportResult(
        pipeline_report=summary,
        experiment_id=experiment_id,
        run_id=run_id,
        report_directory=prepared.relative_report_directory,
        absolute_report_directory=prepared.final_dir,
        files=files,
    )


def build_reports_zip(files: Mapping[str, str | bytes]) -> io.BytesIO:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            if ".." in Path(name).parts or Path(name).is_absolute():
                raise ValueError(f"Unsafe report path: {name}")
            archive.writestr(name, content)
    buffer.seek(0)
    return buffer


def build_reports_zip_from_directory(reports_dir: Path) -> io.BytesIO:
    files: dict[str, bytes] = {}
    for path in reports_dir.iterdir():
        if path.is_file() and path.suffix.lower() in {".json", ".csv"}:
            files[path.name] = path.read_bytes()
    return build_reports_zip(files)


def build_reports_zip_from_files(files: Mapping[str, str | bytes]) -> io.BytesIO:
    return build_reports_zip(files)


def _results_to_dataframe(results: list[EvaluationResult]) -> pd.DataFrame:
    rows = [_to_jsonable(result) for result in results]
    df = pd.DataFrame(rows)
    for column in ["must_include", "must_not_include", "failed_checks"]:
        if column in df:
            df[column] = df[column].apply(lambda value: json.dumps(value or []))
    return df


def _df_to_csv(frame: pd.DataFrame) -> str:
    return frame.to_csv(index=False)


def _annotate_prompt_comparison_results(
    baseline_results: list[EvaluationResult],
    candidate_results: list[EvaluationResult],
    *,
    experiment_id: str,
    run_id: str,
    settings,
) -> None:
    for configuration_id, prompt_name, rows in [
        ("baseline", "Baseline", baseline_results),
        ("candidate", "Candidate", candidate_results),
    ]:
        for result in rows:
            result.experiment_id = experiment_id
            result.run_id = run_id
            result.configuration_id = configuration_id
            result.prompt_name = prompt_name
            result.provider = result.provider or settings.generation_provider
            result.model = result.model or settings.generation_model
            result.judge_provider = result.judge_provider or settings.judge_provider
            result.judge_model = result.judge_model or settings.judge_model


def _configuration_row(
    configuration_id: str,
    prompt_name: str,
    results: list[EvaluationResult],
    metrics: VersionSummary,
) -> dict[str, Any]:
    first = results[0] if results else None
    return {
        "configuration_id": configuration_id,
        "prompt_name": prompt_name,
        "provider": first.provider if first else None,
        "model": first.model if first else None,
        "judge_provider": first.judge_provider if first else None,
        "judge_model": first.judge_model if first else None,
        "dataset_name": first.dataset_name if first else None,
        "dataset_hash": first.dataset_hash if first else None,
        **metrics.model_dump(),
    }


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _to_jsonable(value.model_dump(mode="json"))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(item) for item in value]
    try:
        import numpy as np

        if isinstance(value, np.generic):
            return value.item()
    except ImportError:
        pass
    return value

import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.reports.archive import safe_extract_report_zip as extract_report_zip
from app.reports.persistence import (
    latest_report_directory,
    list_experiment_directories,
    read_latest_pointer,
)
from app.services.evaluation_service import estimate_api_calls


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def load_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (FileNotFoundError, pd.errors.EmptyDataError, OSError):
        return pd.DataFrame()


def safe_extract_report_zip(uploaded_file, target_dir: Path) -> tuple[Path | None, str | None]:
    try:
        return extract_report_zip(uploaded_file, target_dir), None
    except Exception as exc:
        return None, str(exc)


def load_latest_report_pointer(reports_dir: Path) -> dict[str, Any] | None:
    try:
        return read_latest_pointer(reports_dir)
    except Exception:
        return None


def get_latest_report_directory(reports_dir: Path) -> Path | None:
    try:
        return latest_report_directory(reports_dir)
    except Exception:
        return None


def local_experiment_directories(reports_dir: Path) -> list[Path]:
    return list_experiment_directories(reports_dir)


def api_call_estimate(mode: str, test_count: int, prompt_count: int, model_count: int) -> dict[str, int]:
    return estimate_api_calls(
        mode=mode,
        test_count=test_count,
        prompt_count=prompt_count,
        model_count=model_count,
    )


def fairness_warnings(rows: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for field, label in [
        ("dataset_hash", "dataset"),
        ("prompt_hash", "prompt"),
        ("temperature", "temperature"),
        ("max_output_tokens", "max output tokens"),
        ("judge_model", "judge"),
    ]:
        values = {row.get(field) for row in rows if row.get(field) is not None}
        if len(values) > 1:
            warnings.append(f"Comparisons use different {label} values.")
    return warnings

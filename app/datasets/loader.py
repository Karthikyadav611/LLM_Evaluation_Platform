import csv
import json
from pathlib import Path
from typing import Any, BinaryIO

from app.datasets.validator import validate_dataset_records
from app.exceptions import DatasetValidationError
from app.schemas import GoldenTestCase


def load_dataset(file_path: Path, limit: int | None = None) -> list[GoldenTestCase]:
    path = file_path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found at {path}")
    if limit is not None and limit <= 0:
        raise ValueError("Dataset limit must be greater than zero when provided")

    if path.suffix.lower() == ".json":
        records = json.loads(path.read_text(encoding="utf-8"))
    elif path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            records = _normalize_csv_rows(list(csv.DictReader(handle)))
    else:
        raise DatasetValidationError("Datasets must be JSON or CSV")

    cases = validate_dataset_records(records)
    return cases[:limit] if limit is not None else cases


def load_golden_dataset(file_path: Path, limit: int | None = None) -> list[GoldenTestCase]:
    return load_dataset(file_path, limit)


def load_uploaded_dataset(uploaded_file: BinaryIO, filename: str, limit: int | None = None) -> list[GoldenTestCase]:
    suffix = Path(filename).suffix.lower()
    raw = uploaded_file.read()
    text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
    if suffix == ".json":
        records = json.loads(text)
    elif suffix == ".csv":
        records = _normalize_csv_rows(list(csv.DictReader(text.splitlines())))
    else:
        raise DatasetValidationError("Uploaded datasets must be JSON or CSV")
    cases = validate_dataset_records(records)
    return cases[:limit] if limit is not None else cases


def _normalize_csv_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        item = dict(row)
        for key in ("must_include", "must_not_include"):
            value = item.get(key)
            if value in (None, ""):
                item[key] = []
            elif isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    item[key] = parsed if isinstance(parsed, list) else [str(parsed)]
                except json.JSONDecodeError:
                    item[key] = [part.strip() for part in value.split("|") if part.strip()]
        metadata = item.get("metadata")
        if metadata in (None, ""):
            item["metadata"] = {}
        elif isinstance(metadata, str):
            try:
                parsed_metadata = json.loads(metadata)
                item["metadata"] = parsed_metadata if isinstance(parsed_metadata, dict) else {}
            except json.JSONDecodeError:
                item["metadata"] = {}
        normalized.append(item)
    return normalized

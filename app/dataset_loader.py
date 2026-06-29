from pathlib import Path

from app.datasets.loader import load_dataset
from app.schemas import GoldenTestCase


def load_golden_dataset(file_path: Path, limit: int | None = None) -> list[GoldenTestCase]:
    try:
        return load_dataset(file_path, limit)
    except Exception as exc:
        raise ValueError(str(exc)) from exc

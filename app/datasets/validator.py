from collections import Counter
from typing import Any

from app.constants import EXPECTED_BEHAVIORS
from app.exceptions import DatasetValidationError
from app.schemas import GoldenTestCase


def validate_dataset_records(records: list[dict[str, Any]]) -> list[GoldenTestCase]:
    if not isinstance(records, list):
        raise DatasetValidationError("Dataset root must be a list of records")
    if not records:
        raise DatasetValidationError("Dataset is empty")

    cases: list[GoldenTestCase] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(records):
        if not isinstance(item, dict):
            raise DatasetValidationError(f"Test case at index {index} must be an object")
        try:
            case = GoldenTestCase(**item)
        except Exception as exc:
            case_id = item.get("id", "unknown")
            raise DatasetValidationError(
                f"Error validating test case at index {index} (ID: {case_id}): {exc}"
            ) from exc
        if case.id in seen_ids:
            raise DatasetValidationError(f"Duplicate ID detected: {case.id}")
        seen_ids.add(case.id)
        cases.append(case)
    return cases


def summarize_dataset(cases: list[GoldenTestCase]) -> dict[str, Any]:
    category_counts = Counter(case.category for case in cases)
    difficulty_counts = Counter(case.difficulty for case in cases)
    behavior_counts = Counter(case.expected_behavior for case in cases)
    behavior_lookup: dict[str, int] = {str(key): int(value) for key, value in behavior_counts.items()}
    return {
        "total_tests": len(cases),
        "categories": dict(sorted(category_counts.items())),
        "difficulties": dict(sorted(difficulty_counts.items())),
        "expected_behaviors": {behavior: behavior_lookup.get(behavior, 0) for behavior in EXPECTED_BEHAVIORS},
    }

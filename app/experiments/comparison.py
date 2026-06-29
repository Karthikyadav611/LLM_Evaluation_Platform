from collections import defaultdict
from typing import Any

from app.schemas import EvaluationResult, VersionSummary


def compare_model_summaries(summaries: dict[str, VersionSummary]) -> list[dict[str, Any]]:
    rows = []
    for configuration_id, summary in summaries.items():
        rows.append({"configuration_id": configuration_id, **summary.model_dump()})
    return rows


def compare_configuration_results(results: list[EvaluationResult]) -> dict[str, list[str]]:
    by_test: dict[str, list[EvaluationResult]] = defaultdict(list)
    for result in results:
        by_test[result.id].append(result)

    fixed: list[str] = []
    regressed: list[str] = []
    for test_id, rows in by_test.items():
        statuses = [row.final_result for row in rows]
        if "PASS" in statuses and any(status in {"FAIL", "ERROR"} for status in statuses):
            fixed.append(test_id)
            regressed.append(test_id)
    return {"fixed_tests": sorted(set(fixed)), "regressed_tests": sorted(set(regressed))}

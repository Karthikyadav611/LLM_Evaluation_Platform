from app.metrics import calculate_summary
from app.schemas import EvaluationResult, VersionSummary


def summarize_by_configuration(results: list[EvaluationResult]) -> dict[str, VersionSummary]:
    grouped: dict[str, list[EvaluationResult]] = {}
    for result in results:
        grouped.setdefault(result.configuration_id or result.version, []).append(result)
    return {configuration_id: calculate_summary(rows) for configuration_id, rows in grouped.items()}

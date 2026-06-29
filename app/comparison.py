from app.schemas import EvaluationResult, VersionSummary

HIGHER_IS_BETTER = {
    "passed_tests",
    "pass_rate",
    "average_semantic_similarity",
    "average_relevancy",
    "average_faithfulness",
    "average_correctness",
    "safety_pass_rate",
}
LOWER_IS_BETTER = {
    "failed_tests",
    "error_tests",
    "hallucination_rate",
    "average_latency",
    "median_latency",
    "p95_latency",
    "generation_error_count",
    "judge_error_count",
}
INFORMATIONAL = {
    "total_tests",
    "valid_generation_count",
    "valid_judge_count",
    "valid_quality_evaluation_count",
    "valid_evaluation_ratio",
    "total_input_tokens",
    "total_output_tokens",
    "total_tokens",
}
LATENCY_METRICS = {"average_latency", "median_latency", "p95_latency"}


def compare_metrics(
    baseline: VersionSummary,
    candidate: VersionSummary,
    minimum_valid_evaluation_ratio: float = 0.0,
) -> list[dict[str, object]]:
    comparison = []
    b_dict = baseline.model_dump()
    c_dict = candidate.model_dump()

    invalid_quality_comparison = (
        baseline.valid_evaluation_ratio < minimum_valid_evaluation_ratio
        or candidate.valid_evaluation_ratio < minimum_valid_evaluation_ratio
    )

    for key in b_dict:
        b_val = b_dict[key]
        c_val = c_dict[key]
        status = "INFORMATIONAL"

        if key in INFORMATIONAL:
            status = "INFORMATIONAL"
        elif invalid_quality_comparison or key in LATENCY_METRICS and (
            baseline.generation_error_count > 0 or candidate.generation_error_count > 0
        ):
            status = "INVALID COMPARISON"
        if b_val is not None and c_val is not None and isinstance(b_val, (int, float)):
            delta = c_val - b_val
            if status == "INVALID COMPARISON":
                pass
            elif key in HIGHER_IS_BETTER:
                status = "IMPROVEMENT" if delta > 0 else ("REGRESSION" if delta < 0 else "NO CHANGE")
            elif key in LOWER_IS_BETTER:
                status = "IMPROVEMENT" if delta < 0 else ("REGRESSION" if delta > 0 else "NO CHANGE")

        comparison.append(
            {
                "metric": key,
                "baseline": b_val,
                "candidate": c_val,
                "delta": c_val - b_val if _numeric_pair(b_val, c_val) else None,
                "status": status,
            }
        )
    return comparison


def compare_test_results(
    baseline_results: list[EvaluationResult],
    candidate_results: list[EvaluationResult],
) -> list[dict[str, str]]:
    baseline_by_id = {result.id: result for result in baseline_results}
    candidate_by_id = {result.id: result for result in candidate_results}
    all_ids = sorted(baseline_by_id.keys() | candidate_by_id.keys())
    comparison = []

    for test_id in all_ids:
        baseline = baseline_by_id.get(test_id)
        candidate = candidate_by_id.get(test_id)
        baseline_status = baseline.final_result if baseline else "MISSING"
        candidate_status = candidate.final_result if candidate else "MISSING"

        if baseline_status in {"FAIL", "ERROR"} and candidate_status == "PASS":
            status = "FIXED"
        elif baseline_status == "PASS" and candidate_status in {"FAIL", "ERROR"}:
            status = "REGRESSED"
        elif baseline_status == candidate_status:
            status = "NO CHANGE"
        else:
            status = "CHANGED"

        comparison.append(
            {
                "id": test_id,
                "baseline_result": baseline_status,
                "candidate_result": candidate_status,
                "status": status,
            }
        )
    return comparison


def _numeric_pair(left: object, right: object) -> bool:
    return isinstance(left, (int, float)) and isinstance(right, (int, float))

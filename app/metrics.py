from collections.abc import Sequence

from app.schemas import EvaluationResult, VersionSummary


def calculate_summary(results: list[EvaluationResult]) -> VersionSummary:
    total_tests = len(results)
    passed_tests = sum(result.final_result == "PASS" for result in results)
    failed_tests = sum(result.final_result == "FAIL" for result in results)
    error_tests = sum(result.final_result == "ERROR" for result in results)

    valid_generation = [result for result in results if result.generation_error is None]
    valid_judge = [
        result
        for result in valid_generation
        if result.judge_error is None
        and result.relevancy is not None
        and result.faithfulness is not None
        and result.correctness is not None
        and result.safety_passed is not None
        and result.hallucination_detected is not None
    ]

    def average(values: Sequence[float | int | bool | None]) -> float | None:
        clean_values = [float(value) for value in values if value is not None]
        if not clean_values:
            return None
        return round(sum(clean_values) / len(clean_values), 3)

    def percentile(values: list[float], percent: float) -> float | None:
        if not values:
            return None
        sorted_values = sorted(values)
        if len(sorted_values) == 1:
            return round(sorted_values[0], 3)
        rank = (len(sorted_values) - 1) * percent
        lower = int(rank)
        upper = min(lower + 1, len(sorted_values) - 1)
        weight = rank - lower
        value = sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
        return round(value, 3)

    latencies = [
        result.latency_seconds
        for result in valid_generation
        if result.latency_seconds is not None
    ]
    known_costs = [result.estimated_cost for result in results if result.estimated_cost is not None]

    return VersionSummary(
        total_tests=total_tests,
        passed_tests=passed_tests,
        failed_tests=failed_tests,
        error_tests=error_tests,
        pass_rate=round(passed_tests / total_tests, 3) if total_tests else 0.0,
        generation_error_count=sum(result.generation_error is not None for result in results),
        judge_error_count=sum(result.judge_error is not None for result in results),
        valid_generation_count=len(valid_generation),
        valid_judge_count=len(valid_judge),
        valid_quality_evaluation_count=len(valid_judge),
        valid_evaluation_ratio=round(len(valid_judge) / total_tests, 3) if total_tests else 0.0,
        average_semantic_similarity=average(
            [result.semantic_similarity for result in valid_generation]
        ),
        average_relevancy=average([result.relevancy for result in valid_judge]),
        average_faithfulness=average([result.faithfulness for result in valid_judge]),
        average_correctness=average([result.correctness for result in valid_judge]),
        safety_pass_rate=average([result.safety_passed for result in valid_judge]),
        hallucination_rate=average(
            [result.hallucination_detected for result in valid_judge]
        ),
        average_latency=average(latencies),
        median_latency=percentile(latencies, 0.50),
        p95_latency=percentile(latencies, 0.95),
        total_input_tokens=sum(result.input_tokens for result in results),
        total_output_tokens=sum(result.output_tokens for result in results),
        total_tokens=sum(result.total_tokens for result in results),
        total_estimated_cost=round(sum(known_costs), 8) if known_costs else None,
        average_estimated_cost=round(sum(known_costs) / len(known_costs), 8) if known_costs else None,
    )

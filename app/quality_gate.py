from typing import Literal

from app.schemas import QualityGateResult, VersionSummary


def run_validity_checks(
    summary: VersionSummary,
    settings,
    model_connection_ok: bool,
    model_connection_error: str | None = None,
) -> list[QualityGateResult]:
    checks = [
        QualityGateResult(
            name="Model Connection",
            actual=model_connection_ok,
            threshold=True,
            status="PASS" if model_connection_ok else "FAIL",
            reason="Connection succeeded" if model_connection_ok else model_connection_error or "Connection failed",
        ),
        QualityGateResult(
            name="Generation Errors",
            actual=summary.generation_error_count,
            threshold=settings.maximum_generation_errors,
            status=(
                "PASS"
                if summary.generation_error_count <= settings.maximum_generation_errors
                else "FAIL"
            ),
            reason="Generation error count must stay within the configured maximum",
        ),
        QualityGateResult(
            name="Judge Errors",
            actual=summary.judge_error_count,
            threshold=settings.maximum_judge_errors,
            status="PASS" if summary.judge_error_count <= settings.maximum_judge_errors else "FAIL",
            reason="Judge error count must stay within the configured maximum",
        ),
        QualityGateResult(
            name="Valid Evaluation Ratio",
            actual=summary.valid_evaluation_ratio,
            threshold=settings.minimum_valid_evaluation_ratio,
            status=(
                "PASS"
                if summary.valid_evaluation_ratio >= settings.minimum_valid_evaluation_ratio
                else "FAIL"
            ),
            reason="Enough rows must have successful generation and judge metrics",
        ),
    ]

    required_metrics = {
        "pass_rate": summary.pass_rate,
        "average_correctness": summary.average_correctness,
        "average_faithfulness": summary.average_faithfulness,
        "safety_pass_rate": summary.safety_pass_rate,
        "hallucination_rate": summary.hallucination_rate,
        "p95_latency": summary.p95_latency,
    }
    missing_metrics = [name for name, value in required_metrics.items() if value is None]
    checks.append(
        QualityGateResult(
            name="Required Metric Availability",
            actual=", ".join(missing_metrics) if missing_metrics else "available",
            threshold="all required metrics available",
            status="PASS" if not missing_metrics else "UNAVAILABLE",
            reason="Required quality metrics must be available before applying quality gates",
        )
    )
    return checks


def run_quality_gates(summary: VersionSummary, settings) -> list[QualityGateResult]:
    gates = []
    metrics = [
        ("Pass Rate", summary.pass_rate, settings.minimum_pass_rate, "HIGHER"),
        ("Correctness", summary.average_correctness, settings.minimum_correctness, "HIGHER"),
        ("Relevancy", summary.average_relevancy, getattr(settings, "minimum_relevancy", 0.0), "HIGHER"),
        ("Faithfulness", summary.average_faithfulness, settings.minimum_faithfulness, "HIGHER"),
        ("Safety Pass Rate", summary.safety_pass_rate, settings.minimum_safety_pass_rate, "HIGHER"),
        (
            "Hallucination Rate",
            summary.hallucination_rate,
            settings.maximum_hallucination_rate,
            "LOWER",
        ),
        ("Latency P95", summary.p95_latency, settings.maximum_p95_latency, "LOWER"),
        ("Generation Errors", summary.generation_error_count, settings.maximum_generation_errors, "LOWER"),
        ("Judge Errors", summary.judge_error_count, settings.maximum_judge_errors, "LOWER"),
        ("Valid Evaluation Ratio", summary.valid_evaluation_ratio, settings.minimum_valid_evaluation_ratio, "HIGHER"),
    ]
    if getattr(settings, "maximum_average_cost", None) is not None:
        metrics.append(("Average Cost", summary.average_estimated_cost, settings.maximum_average_cost, "LOWER"))

    for name, actual, threshold, direction in metrics:
        if actual is None:
            status: Literal["PASS", "FAIL", "UNAVAILABLE"] = "UNAVAILABLE"
            reason = "Metric is unavailable"
        else:
            passed = actual >= threshold if direction == "HIGHER" else actual <= threshold
            status = "PASS" if passed else "FAIL"
            comparator = ">=" if direction == "HIGHER" else "<="
            reason = f"{actual} must be {comparator} {threshold}"

        gates.append(
            QualityGateResult(
                name=name,
                actual=actual,
                threshold=threshold,
                status=status,
                reason=reason,
            )
        )

    return gates


def determine_pipeline_status(
    validity_checks: list[QualityGateResult],
    quality_gates: list[QualityGateResult],
) -> Literal["PASS", "FAIL", "ERROR"]:
    if any(check.status != "PASS" for check in validity_checks):
        return "ERROR"
    if any(gate.status != "PASS" for gate in quality_gates):
        return "FAIL"
    return "PASS"

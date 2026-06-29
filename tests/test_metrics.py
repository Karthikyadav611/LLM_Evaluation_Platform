from app.metrics import calculate_summary


def test_metrics_with_valid_rows(make_result):
    summary = calculate_summary(
        [
            make_result("one", final_result="PASS", latency_seconds=1.0),
            make_result("two", final_result="FAIL", latency_seconds=3.0, correctness=0.4),
        ]
    )

    assert summary.total_tests == 2
    assert summary.pass_rate == 0.5
    assert summary.average_latency == 2.0
    assert summary.p95_latency == 2.9
    assert summary.hallucination_rate == 0.0


def test_metrics_with_partial_errors_do_not_count_failures_as_fast_or_unsafe(make_result):
    summary = calculate_summary(
        [
            make_result("pass", final_result="PASS", latency_seconds=2.0),
            make_result(
                "generation_error",
                final_result="ERROR",
                generation_error="timeout",
                latency_seconds=None,
                correctness=None,
                faithfulness=None,
                relevancy=None,
                safety_passed=None,
                hallucination_detected=None,
            ),
            make_result(
                "judge_error",
                final_result="ERROR",
                judge_error="bad json",
                correctness=None,
                faithfulness=None,
                relevancy=None,
                safety_passed=None,
                hallucination_detected=None,
            ),
        ]
    )

    assert summary.generation_error_count == 1
    assert summary.judge_error_count == 1
    assert summary.average_latency == 1.5
    assert summary.safety_pass_rate == 1.0
    assert summary.hallucination_rate == 0.0
    assert summary.valid_quality_evaluation_count == 1


def test_metrics_all_error_run_has_none_for_unavailable_quality_metrics(make_result):
    summary = calculate_summary(
        [
            make_result(
                "one",
                final_result="ERROR",
                generation_error="timeout",
                latency_seconds=None,
                correctness=None,
                faithfulness=None,
                relevancy=None,
                safety_passed=None,
                hallucination_detected=None,
            )
        ]
    )

    assert summary.pass_rate == 0.0
    assert summary.average_correctness is None
    assert summary.average_latency is None
    assert summary.valid_evaluation_ratio == 0.0

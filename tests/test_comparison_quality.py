from app.comparison import compare_metrics, compare_test_results
from app.config import Settings
from app.metrics import calculate_summary
from app.quality_gate import determine_pipeline_status, run_quality_gates, run_validity_checks


def test_comparison_directionality_and_informational_metrics(make_result):
    baseline = calculate_summary([make_result("one", final_result="FAIL", correctness=0.4)])
    candidate = calculate_summary([make_result("one", final_result="PASS", correctness=0.9)])

    rows = {row["metric"]: row for row in compare_metrics(baseline, candidate)}

    assert rows["pass_rate"]["status"] == "IMPROVEMENT"
    assert rows["failed_tests"]["status"] == "IMPROVEMENT"
    assert rows["total_tokens"]["status"] == "INFORMATIONAL"


def test_latency_comparison_invalid_when_generation_failed(make_result):
    baseline = calculate_summary([make_result("one", final_result="PASS")])
    candidate = calculate_summary(
        [
            make_result("one", final_result="PASS"),
            make_result("two", final_result="ERROR", generation_error="timeout", latency_seconds=None),
        ]
    )

    rows = {row["metric"]: row for row in compare_metrics(baseline, candidate)}

    assert rows["p95_latency"]["status"] == "INVALID COMPARISON"


def test_test_level_comparison_identifies_fixed_and_regressed(make_result):
    rows = compare_test_results(
        [make_result("fixed", final_result="FAIL"), make_result("regressed", final_result="PASS")],
        [make_result("fixed", final_result="PASS"), make_result("regressed", final_result="FAIL")],
    )
    statuses = {row["id"]: row["status"] for row in rows}

    assert statuses == {"fixed": "FIXED", "regressed": "REGRESSED"}


def test_quality_gate_statuses_pass_fail_and_error(make_result):
    settings = Settings(_env_file=None)
    good_summary = calculate_summary([make_result("one", final_result="PASS")])
    bad_summary = calculate_summary([make_result("one", final_result="FAIL", correctness=0.2)])
    error_summary = calculate_summary(
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

    assert determine_pipeline_status(
        run_validity_checks(good_summary, settings, True),
        run_quality_gates(good_summary, settings),
    ) == "PASS"
    assert determine_pipeline_status(
        run_validity_checks(bad_summary, settings, True),
        run_quality_gates(bad_summary, settings),
    ) == "FAIL"
    assert determine_pipeline_status(
        run_validity_checks(error_summary, settings, True),
        run_quality_gates(error_summary, settings),
    ) == "ERROR"

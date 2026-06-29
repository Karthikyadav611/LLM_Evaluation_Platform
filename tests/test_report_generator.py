import json
import zipfile
from io import BytesIO

import pandas as pd
import pytest

from app.comparison import compare_metrics, compare_test_results
from app.config import Settings
from app.metrics import calculate_summary
from app.quality_gate import run_quality_gates, run_validity_checks
from app.report_generator import build_reports_zip_from_files, export_reports
from app.reports.persistence import prepare_experiment_directory


def test_export_reports_writes_all_required_artifacts(tmp_path, make_result):
    baseline_results = [make_result("one", final_result="FAIL")]
    candidate_results = [make_result("one", final_result="PASS")]
    baseline_metrics = calculate_summary(baseline_results)
    candidate_metrics = calculate_summary(candidate_results)
    settings = Settings(_env_file=None)
    settings.experiment_id = "exp-test"

    result = export_reports(
        tmp_path,
        baseline_results,
        candidate_results,
        baseline_metrics,
        candidate_metrics,
        compare_metrics(baseline_metrics, candidate_metrics),
        compare_test_results(baseline_results, candidate_results),
        run_validity_checks(candidate_metrics, settings, True),
        run_quality_gates(candidate_metrics, settings),
        settings,
        "PASS",
    )

    expected = {
        "baseline_evaluation_results.csv",
        "candidate_evaluation_results.csv",
        "failed_candidate_tests.csv",
        "prompt_comparison.csv",
        "test_level_comparison.csv",
        "evaluation_summary.json",
        "experiment_summary.json",
        "configuration_results.csv",
        "test_results.csv",
        "model_comparison.csv",
        "quality_gates.csv",
        "failed_tests.csv",
        "fixed_tests.csv",
        "regressed_tests.csv",
    }
    report_dir = tmp_path / "experiments" / "exp-test"
    assert expected == {path.name for path in report_dir.iterdir()}

    latest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert latest["experiment_id"] == "exp-test"
    assert latest["report_directory"] == "reports/experiments/exp-test" or latest["report_directory"].endswith("experiments/exp-test")

    summary = json.loads((report_dir / "evaluation_summary.json").read_text(encoding="utf-8"))
    assert summary["pipeline_status"] == "PASS"
    assert summary["report_directory"] == result.report_directory
    assert "GROQ_API_KEY" not in (report_dir / "evaluation_summary.json").read_text(encoding="utf-8")

    comparison = pd.read_csv(report_dir / "test_level_comparison.csv")
    assert comparison.loc[0, "status"] == "FIXED"

    with zipfile.ZipFile(BytesIO(build_reports_zip_from_files(result.files).getvalue())) as archive:
        assert sorted(archive.namelist()) == sorted(result.files)


def test_export_reports_persists_fail_and_error_statuses(tmp_path, make_result):
    settings = Settings(_env_file=None)
    for status in ["FAIL", "ERROR"]:
        settings.experiment_id = f"exp-{status.lower()}"
        baseline_results = [make_result("one", final_result=status)]
        candidate_results = [make_result("one", final_result=status)]
        baseline_metrics = calculate_summary(baseline_results)
        candidate_metrics = calculate_summary(candidate_results)

        result = export_reports(
            tmp_path,
            baseline_results,
            candidate_results,
            baseline_metrics,
            candidate_metrics,
            compare_metrics(baseline_metrics, candidate_metrics),
            compare_test_results(baseline_results, candidate_results),
            run_validity_checks(candidate_metrics, settings, True),
            run_quality_gates(candidate_metrics, settings),
            settings,
            status,
        )

        assert (result.absolute_report_directory / "experiment_summary.json").exists()
        latest = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
        assert latest["status"] == status


def test_duplicate_experiment_id_gets_unique_suffix(tmp_path, make_result):
    settings = Settings(_env_file=None)
    settings.experiment_id = "same-exp"
    baseline_results = [make_result("one", final_result="PASS")]
    candidate_results = [make_result("one", final_result="PASS")]
    baseline_metrics = calculate_summary(baseline_results)
    candidate_metrics = calculate_summary(candidate_results)
    args = (
        baseline_results,
        candidate_results,
        baseline_metrics,
        candidate_metrics,
        compare_metrics(baseline_metrics, candidate_metrics),
        compare_test_results(baseline_results, candidate_results),
        run_validity_checks(candidate_metrics, settings, True),
        run_quality_gates(candidate_metrics, settings),
        settings,
        "PASS",
    )

    first = export_reports(tmp_path, *args)
    second = export_reports(tmp_path, *args)

    assert first.experiment_id == "same-exp"
    assert second.experiment_id == "same-exp-1"
    assert first.absolute_report_directory.exists()
    assert second.absolute_report_directory.exists()


def test_experiment_id_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError, match="path"):
        prepare_experiment_directory(tmp_path, "../bad")

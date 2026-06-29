import io
import zipfile

import pytest

from dashboard.helpers import api_call_estimate, safe_extract_report_zip


def test_api_call_estimate_for_prompt_comparison():
    estimate = api_call_estimate("prompt_comparison", test_count=3, prompt_count=2, model_count=1)

    assert estimate == {"generation_calls": 6, "judge_calls": 6, "approximate_total": 12}


def test_report_zip_extraction_rejects_path_traversal(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("../evil.txt", "bad")
    buffer.seek(0)

    extracted, error = safe_extract_report_zip(buffer, tmp_path)

    assert extracted is None
    assert error


def test_database_persistence_smoke(tmp_path):
    pytest.importorskip("sqlalchemy")
    from app.schemas import ExperimentConfiguration, ExperimentSummary
    from app.storage.database import create_database_engine, create_session_factory
    from app.storage.migrations import initialize_database
    from app.storage.repositories import ExperimentRepository

    engine = create_database_engine(f"sqlite:///{tmp_path / 'eval.db'}")
    initialize_database(engine)
    repository = ExperimentRepository(create_session_factory(engine))
    configuration = ExperimentConfiguration(
        experiment_id="exp",
        run_id="run",
        configuration_id="cfg",
        prompt_name="prompt",
        prompt_text="text",
        prompt_hash="hash",
        provider="groq",
        model="model",
        judge_provider="groq",
        judge_model="judge",
        dataset_name="dataset",
        dataset_hash="dataset-hash",
    )
    repository.save_experiment(
        ExperimentSummary(
            experiment_id="exp",
            run_id="run",
            mode="matrix",
            dataset_name="dataset",
            dataset_hash="dataset-hash",
            started_at="now",
            configurations=[configuration],
        )
    )

    assert repository.list_experiments()[0]["experiment_id"] == "exp"


def test_sqlite_record_contains_report_directory(tmp_path, make_result):
    pytest.importorskip("sqlalchemy")
    from app.schemas import ExperimentConfiguration, ExperimentSummary
    from app.storage.database import create_database_engine, create_session_factory
    from app.storage.migrations import initialize_database
    from app.storage.repositories import ExperimentRepository

    engine = create_database_engine(f"sqlite:///{tmp_path / 'eval.db'}")
    initialize_database(engine)
    repository = ExperimentRepository(create_session_factory(engine))
    configuration = ExperimentConfiguration(
        experiment_id="exp-report",
        run_id="run",
        configuration_id="cfg",
        prompt_name="prompt",
        prompt_text="text",
        prompt_hash="hash",
        provider="groq",
        model="model",
        judge_provider="groq",
        judge_model="judge",
        dataset_name="dataset",
        dataset_hash="dataset-hash",
        status="PASS",
    )
    repository.save_completed_run(
        summary=ExperimentSummary(
            experiment_id="exp-report",
            run_id="run",
            mode="prompt_comparison",
            dataset_name="dataset",
            dataset_hash="dataset-hash",
            started_at="now",
            status="PASS",
            configurations=[configuration],
        ),
        results=[make_result("one", final_result="PASS").model_copy(update={
            "experiment_id": "exp-report",
            "run_id": "run",
            "configuration_id": "cfg",
        })],
        metric_summaries={},
        quality_gates=[],
        report_directory="reports/experiments/exp-report",
        report_files=["experiment_summary.json"],
    )

    row = repository.get_experiment("exp-report")
    assert row
    assert row["report_directory"] == "reports/experiments/exp-report"
    assert row["completed_at"]

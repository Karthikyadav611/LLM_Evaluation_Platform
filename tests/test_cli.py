from argparse import Namespace

from app.config import Settings
from app.schemas import GoldenTestCase
from scripts import run_evaluation


def test_cli_returns_error_without_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(
        run_evaluation,
        "parse_args",
        lambda: Namespace(
            test_limit=None,
            no_delay=True,
            dataset=tmp_path / "dataset.json",
            reports_dir=tmp_path / "reports",
        ),
    )
    monkeypatch.setattr(run_evaluation, "Settings", lambda: Settings(_env_file=None))

    assert run_evaluation.main() == 2


def test_cli_prints_experiment_and_report_path(monkeypatch, tmp_path, make_result, capsys):
    reports_dir = tmp_path / "reports"
    settings = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'eval.db'}")
    settings.experiment_id = "cli-exp"

    monkeypatch.setattr(
        run_evaluation,
        "parse_args",
        lambda: Namespace(
            test_limit=1,
            no_delay=True,
            generation_provider=None,
            generation_model=None,
            judge_provider=None,
            judge_model=None,
            dataset=tmp_path / "dataset.json",
            reports_dir=reports_dir,
        ),
    )
    monkeypatch.setattr(run_evaluation, "Settings", lambda: settings)
    monkeypatch.setattr(Settings, "require_api_key", lambda self, provider: "test-key")
    monkeypatch.setattr(run_evaluation, "create_provider", lambda *args, **kwargs: FakeProvider())
    monkeypatch.setattr(
        run_evaluation,
        "load_golden_dataset",
        lambda path, limit=None: [
            GoldenTestCase(
                id="one",
                category="support",
                difficulty="easy",
                question="Question?",
                context="Context.",
                expected_answer="Answer.",
                must_include=[],
                must_not_include=[],
                expected_behavior="answer",
            )
        ],
    )
    monkeypatch.setattr(
        run_evaluation,
        "evaluate_prompt_version",
        lambda *args, **kwargs: [make_result("one", final_result="PASS")],
    )
    monkeypatch.setattr(run_evaluation.Path, "read_bytes", lambda self: b"dataset")

    assert run_evaluation.main() == 0
    output = capsys.readouterr().out
    assert "Experiment ID: cli-exp" in output
    assert "Reports saved to:" in output
    assert (reports_dir / "experiments" / "cli-exp" / "experiment_summary.json").exists()


class FakeProvider:
    default_temperature = 0.0
    default_max_output_tokens = 1024

    def check_connection(self):
        return True, None

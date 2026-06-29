import csv

from app.datasets.loader import load_dataset
from app.experiments.matrix_runner import expand_prompt_model_matrix
from app.prompts.versioning import hash_prompt


def test_load_dataset_supports_csv(tmp_path):
    path = tmp_path / "dataset.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "id",
                "category",
                "difficulty",
                "question",
                "context",
                "expected_answer",
                "must_include",
                "must_not_include",
                "expected_behavior",
                "metadata",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "id": "csv-1",
                "category": "support",
                "difficulty": "easy",
                "question": "Q?",
                "context": "Context.",
                "expected_answer": "Answer.",
                "must_include": "Answer",
                "must_not_include": "",
                "expected_behavior": "answer",
                "metadata": "{}",
            }
        )

    cases = load_dataset(path)

    assert cases[0].id == "csv-1"
    assert cases[0].must_include == ["Answer"]


def test_prompt_hash_is_stable_and_matrix_expands():
    assert hash_prompt("hello\n") == hash_prompt("hello")
    configs = expand_prompt_model_matrix(
        experiment_id="exp",
        run_id="run",
        prompts={"baseline": "prompt a", "candidate": "prompt b"},
        provider_models=[("groq", "m1"), ("openai", "m2")],
        judge_provider="gemini",
        judge_model="judge",
        dataset_name="data",
        dataset_hash="hash",
    )

    assert len(configs) == 4
    assert len({config.configuration_id for config in configs}) == 4

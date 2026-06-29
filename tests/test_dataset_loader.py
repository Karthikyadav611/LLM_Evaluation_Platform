import json

import pytest

from app.dataset_loader import load_golden_dataset


def test_load_dataset_validates_and_limits(tmp_path):
    path = tmp_path / "dataset.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": "one",
                    "category": "support",
                    "difficulty": "easy",
                    "question": "Question?",
                    "context": "Context has an answer.",
                    "expected_answer": "An answer.",
                    "must_include": ["answer"],
                    "must_not_include": [],
                    "expected_behavior": "answer",
                },
                {
                    "id": "two",
                    "category": "support",
                    "difficulty": "easy",
                    "question": "Question?",
                    "context": "Context has an answer.",
                    "expected_answer": "An answer.",
                    "must_include": [],
                    "must_not_include": [],
                    "expected_behavior": "clarify",
                },
            ]
        ),
        encoding="utf-8",
    )

    cases = load_golden_dataset(path, limit=1)

    assert len(cases) == 1
    assert cases[0].id == "one"


def test_load_dataset_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "dataset.json"
    case = {
        "id": "dup",
        "category": "support",
        "difficulty": "easy",
        "question": "Question?",
        "context": "Context.",
        "expected_answer": "Answer.",
        "must_include": [],
        "must_not_include": [],
        "expected_behavior": "answer",
    }
    path.write_text(json.dumps([case, case]), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate ID"):
        load_golden_dataset(path)


def test_load_dataset_rejects_invalid_schema(tmp_path):
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps([{"id": "bad", "expected_behavior": "guess"}]), encoding="utf-8")

    with pytest.raises(ValueError, match="Error validating"):
        load_golden_dataset(path)

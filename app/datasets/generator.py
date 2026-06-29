import json

from app.datasets.validator import validate_dataset_records
from app.schemas import GoldenTestCase


def build_dataset_generation_prompt(source_text: str, count: int = 10) -> str:
    return (
        "Create draft LLM evaluation test cases from the source text. "
        "Return only JSON array records with fields id, category, difficulty, question, "
        "context, expected_answer, must_include, must_not_include, expected_behavior, metadata. "
        "Allowed expected_behavior values are answer, unanswerable, clarify, refuse. "
        "Label metadata.generated_draft as true and metadata.requires_human_review as true.\n\n"
        f"Number of draft cases: {count}\n\nSource text:\n{source_text}"
    )


def parse_generated_dataset(raw_json: str) -> list[GoldenTestCase]:
    records = json.loads(raw_json)
    cases = validate_dataset_records(records)
    return [
        case.model_copy(
            update={
                "metadata": {
                    **case.metadata,
                    "generated_draft": True,
                    "requires_human_review": True,
                }
            }
        )
        for case in cases
    ]

from typing import Any

from app.evaluators.base import BaseEvaluator
from app.schemas import GoldenTestCase


class SemanticSimilarityEvaluator(BaseEvaluator):
    name = "semantic_similarity"

    def evaluate(self, actual: str, case: GoldenTestCase) -> dict[str, Any]:
        from app.evaluators_legacy import Evaluator

        return {"score": Evaluator().calculate_similarity(actual, case.expected_answer)}

from typing import Any

from app.evaluators.base import BaseEvaluator
from app.schemas import GoldenTestCase


class KeywordEvaluator(BaseEvaluator):
    name = "keyword"

    def evaluate(self, actual: str, case: GoldenTestCase) -> dict[str, Any]:
        from app.evaluators_legacy import Evaluator

        evaluator = Evaluator()
        return evaluator.check_keywords(actual, case.must_include, case.must_not_include)

from typing import Any

from app.evaluators.base import BaseEvaluator
from app.schemas import GoldenTestCase


class BehaviorEvaluator(BaseEvaluator):
    name = "behavior"

    def evaluate(self, actual: str, case: GoldenTestCase) -> dict[str, Any]:
        from app.evaluators_legacy import Evaluator

        return {"passed": Evaluator().check_behavior(actual, case.expected_behavior)}

from app.evaluators.base import BaseEvaluator
from app.evaluators.behavior import BehaviorEvaluator
from app.evaluators.keyword import KeywordEvaluator
from app.evaluators.safety import SafetyEvaluator
from app.evaluators.semantic_similarity import SemanticSimilarityEvaluator


class EvaluatorRegistry:
    def __init__(self) -> None:
        self._evaluators: dict[str, BaseEvaluator] = {}

    def register(self, evaluator: BaseEvaluator) -> None:
        self._evaluators[evaluator.name] = evaluator

    def get(self, name: str) -> BaseEvaluator:
        return self._evaluators[name]

    def names(self) -> list[str]:
        return sorted(self._evaluators)


def default_registry() -> EvaluatorRegistry:
    registry = EvaluatorRegistry()
    registry.register(KeywordEvaluator())
    registry.register(SemanticSimilarityEvaluator())
    registry.register(BehaviorEvaluator())
    registry.register(SafetyEvaluator())
    return registry

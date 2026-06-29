from abc import ABC, abstractmethod
from typing import Any

from app.schemas import GoldenTestCase


class BaseEvaluator(ABC):
    name: str

    @abstractmethod
    def evaluate(self, actual: str, case: GoldenTestCase) -> dict[str, Any]:
        ...

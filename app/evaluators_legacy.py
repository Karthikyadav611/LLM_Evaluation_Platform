import string
from typing import Any


class Evaluator:
    def normalize_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.lower()
        text = text.translate(str.maketrans("", "", string.punctuation))
        return " ".join(text.split())

    def check_keywords(
        self,
        actual: str,
        must_include: list[str],
        must_not_include: list[str],
    ) -> dict[str, Any]:
        norm_actual = self.normalize_text(actual)

        missing = [kw for kw in must_include if self.normalize_text(kw) not in norm_actual]
        forbidden = [kw for kw in must_not_include if self.normalize_text(kw) in norm_actual]

        return {
            "passed": len(missing) == 0 and len(forbidden) == 0,
            "missing": missing,
            "forbidden_found": forbidden,
        }

    def calculate_similarity(self, actual: str, expected: str) -> float | None:
        if not actual or not expected:
            return None
        return self._token_similarity(actual, expected)

    def check_behavior(self, actual: str, behavior: str) -> bool:
        norm_actual = self.normalize_text(actual)
        if not norm_actual:
            return False
        if behavior == "unanswerable":
            keywords = [
                "not available",
                "not provided",
                "does not include",
                "does not mention",
                "do not have",
                "dont have",
                "insufficient information",
                "not enough information",
                "not in the context",
                "cannot determine",
            ]
            return any(k in norm_actual for k in keywords)
        if behavior == "clarify":
            phrases = [
                "please specify",
                "could you",
                "can you clarify",
                "which",
                "what type",
                "let me know",
                "need more information",
            ]
            return "?" in actual or any(phrase in norm_actual for phrase in phrases)
        if behavior == "refuse":
            phrases = [
                "cannot",
                "cant",
                "will not",
                "unable to",
                "not able to",
                "do not reveal",
                "wont reveal",
                "cannot provide",
                "cannot fulfill",
                "must refuse",
            ]
            return any(phrase in norm_actual for phrase in phrases)
        return len(norm_actual) > 5

    @staticmethod
    def _token_similarity(actual: str, expected: str) -> float:
        actual_tokens = set(actual.lower().split())
        expected_tokens = set(expected.lower().split())
        if not actual_tokens or not expected_tokens:
            return 0.0
        score = len(actual_tokens & expected_tokens) / len(actual_tokens | expected_tokens)
        return round(float(score), 3)

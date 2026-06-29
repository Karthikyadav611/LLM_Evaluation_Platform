import pytest

from app.schemas import EvaluationResult, GoldenTestCase


@pytest.fixture
def make_case():
    def _make_case(case_id: str = "case_1", expected_behavior: str = "answer") -> GoldenTestCase:
        return GoldenTestCase(
            id=case_id,
            category="support",
            difficulty="easy",
            question="What is the return window?",
            context="Returns are accepted within 30 days with a receipt.",
            expected_answer="Returns are accepted within 30 days.",
            must_include=["30 days"],
            must_not_include=["90 days"],
            expected_behavior=expected_behavior,
        )

    return _make_case


@pytest.fixture
def make_result(
):
    def _make_result(
        result_id: str = "case_1",
        final_result: str = "PASS",
        generation_error: str | None = None,
        judge_error: str | None = None,
        latency_seconds: float | None = 1.0,
        correctness: float | None = 0.9,
        faithfulness: float | None = 0.9,
        relevancy: float | None = 0.9,
        safety_passed: bool | None = True,
        hallucination_detected: bool | None = False,
    ) -> EvaluationResult:
        return EvaluationResult(
            version="Candidate",
            id=result_id,
            category="support",
            difficulty="easy",
            question="What is the return window?",
            context="Returns are accepted within 30 days with a receipt.",
            expected_answer="Returns are accepted within 30 days.",
            expected_behavior="answer",
            must_include=["30 days"],
            must_not_include=["90 days"],
            actual_answer="" if generation_error else "Returns are accepted within 30 days.",
            keyword_passed=generation_error is None,
            forbidden_terms_passed=generation_error is None,
            behavior_passed=generation_error is None,
            semantic_similarity=None if generation_error else 0.8,
            relevancy=relevancy,
            faithfulness=faithfulness,
            correctness=correctness,
            safety_passed=safety_passed,
            hallucination_detected=hallucination_detected,
            judge_reason="ok" if not judge_error else "",
            failed_checks=[] if final_result == "PASS" else [final_result.lower()],
            latency_seconds=latency_seconds,
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            generation_error=generation_error,
            judge_error=judge_error,
            final_result=final_result,
        )

    return _make_result

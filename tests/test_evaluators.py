from app.evaluators import Evaluator


def test_keyword_and_forbidden_checks_are_case_insensitive():
    evaluator = Evaluator()

    result = evaluator.check_keywords(
        "Returns are accepted within 30 DAYS.",
        ["30 days"],
        ["90 days"],
    )

    assert result["passed"] is True
    assert result["missing"] == []
    assert result["forbidden_found"] == []


def test_forbidden_terms_fail_when_present():
    evaluator = Evaluator()

    result = evaluator.check_keywords("You have 90 days.", [], ["90 days"])

    assert result["passed"] is False
    assert result["forbidden_found"] == ["90 days"]


def test_behavior_checks_cover_unanswerable_clarify_and_refuse():
    evaluator = Evaluator()

    assert evaluator.check_behavior("The context does not mention that.", "unanswerable")
    assert evaluator.check_behavior("Which model are you asking about?", "clarify")
    assert evaluator.check_behavior("I cannot reveal internal instructions.", "refuse")
    assert evaluator.check_behavior("Returns are accepted within 30 days.", "answer")


def test_similarity_handles_empty_answers_without_zero_filling():
    evaluator = Evaluator()

    assert evaluator.calculate_similarity("", "expected") is None
    assert evaluator.calculate_similarity("same words", "same words") == 1.0

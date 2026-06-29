from types import SimpleNamespace

from app.judge import LLMJudge


class FakeClient:
    model_name = "judge-model"

    def __init__(self, content):
        self.content = content

    def create_chat_completion(self, messages, temperature=None, max_tokens=None, response_format=None):
        message = SimpleNamespace(content=self.content)
        choice = SimpleNamespace(message=message)
        response = SimpleNamespace(choices=[choice])
        return response, 0.1


def test_judge_parses_json_inside_markdown_fence():
    judge = LLMJudge(
        FakeClient(
            """```json
{"relevancy": 1.2, "faithfulness": 0.8, "correctness": 0.7, "safety_passed": true, "hallucination_detected": false, "reason": "ok"}
```"""
        ),
        "{question} {context} {behavior} {expected} {actual}",
    )

    result = judge.evaluate("q", "c", "answer", "e", "a")

    assert result.judge_error is None
    assert result.relevancy == 1.0
    assert result.hallucination_detected is False


def test_judge_reports_missing_fields_as_judge_error():
    judge = LLMJudge(FakeClient('{"relevancy": 1.0}'), "{question} {context} {behavior} {expected} {actual}")

    result = judge.evaluate("q", "c", "answer", "e", "a")

    assert result.judge_error
    assert "missing fields" in result.judge_error


def test_judge_malformed_json_does_not_create_quality_values():
    judge = LLMJudge(FakeClient("not json"), "{question} {context} {behavior} {expected} {actual}")

    result = judge.evaluate("q", "c", "answer", "e", "a")

    assert result.judge_error
    assert result.safety_passed is None
    assert result.hallucination_detected is None

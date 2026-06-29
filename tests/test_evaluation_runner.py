from app.evaluation_runner import evaluate_prompt_version
from app.schemas import GenerationResult, JudgeResult


class FakeGenerationClient:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def generate_answer(self, system_prompt, question, context):
        self.calls += 1
        return self.results.pop(0)


class FakeJudge:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def evaluate(self, question, context, behavior, expected, actual):
        self.calls += 1
        return self.result


class FakeEvaluator:
    def check_keywords(self, actual, must_include, must_not_include):
        return {"passed": True, "missing": [], "forbidden_found": []}

    def calculate_similarity(self, actual, expected):
        return 1.0

    def check_behavior(self, actual, behavior):
        return True


def test_runner_calls_judge_once_for_successful_generation(make_case):
    gen_client = FakeGenerationClient([GenerationResult(answer="ok", latency_seconds=0.5)])
    judge = FakeJudge(
        JudgeResult(
            relevancy=0.9,
            faithfulness=0.9,
            correctness=0.9,
            safety_passed=True,
            hallucination_detected=False,
            reason="ok",
        )
    )

    results = evaluate_prompt_version(
        "Candidate", "prompt", [make_case()], gen_client, judge, FakeEvaluator(), delay=0
    )

    assert gen_client.calls == 1
    assert judge.calls == 1
    assert results[0].final_result == "PASS"


def test_runner_skips_judge_on_generation_error(make_case):
    gen_client = FakeGenerationClient(
        [GenerationResult(answer="", generation_error="provider failed")]
    )
    judge = FakeJudge(JudgeResult())

    results = evaluate_prompt_version(
        "Candidate", "prompt", [make_case()], gen_client, judge, FakeEvaluator(), delay=0
    )

    assert gen_client.calls == 1
    assert judge.calls == 0
    assert results[0].final_result == "ERROR"
    assert results[0].latency_seconds is None

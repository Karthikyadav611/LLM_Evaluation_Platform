import time
from collections.abc import Mapping
from typing import Any, Literal

from tqdm import tqdm

from app.constants import DEFAULT_QUALITY_THRESHOLDS
from app.evaluators import Evaluator
from app.judge import LLMJudge
from app.schemas import EvaluationResult, GoldenTestCase


def evaluate_prompt_version(
    version_name: str,
    system_prompt: str,
    test_cases: list[GoldenTestCase],
    gen_client: Any,
    judge_instance: LLMJudge,
    evaluator: Evaluator,
    delay: float = 1.0,
    quality_thresholds: Mapping[str, float] | None = None,
) -> list[EvaluationResult]:
    results = []
    thresholds = dict(DEFAULT_QUALITY_THRESHOLDS)
    if quality_thresholds:
        thresholds.update(quality_thresholds)

    print(f"\nRunning evaluation for: {version_name}")
    for case in tqdm(test_cases):
        gen = gen_client.generate_answer(system_prompt, case.question, case.context)
        generation_error = gen.generation_error or gen.error_message

        if generation_error:
            results.append(
                EvaluationResult(
                    version=version_name,
                    id=case.id,
                    category=case.category,
                    difficulty=case.difficulty,
                    question=case.question,
                    context=case.context,
                    expected_answer=case.expected_answer,
                    expected_behavior=case.expected_behavior,
                    must_include=case.must_include,
                    must_not_include=case.must_not_include,
                    actual_answer=gen.answer,
                    keyword_passed=False,
                    forbidden_terms_passed=False,
                    behavior_passed=False,
                    semantic_similarity=None,
                    relevancy=None,
                    faithfulness=None,
                    correctness=None,
                    safety_passed=None,
                    hallucination_detected=None,
                    judge_reason="",
                    failed_checks=["generation_error"],
                    latency_seconds=gen.latency_seconds,
                    input_tokens=gen.input_tokens,
                    output_tokens=gen.output_tokens,
                    total_tokens=gen.total_tokens,
                    estimated_cost=gen.estimated_cost,
                    generation_error=generation_error,
                    judge_error=None,
                    final_result="ERROR",
                    provider=gen.provider or getattr(gen_client, "provider", None),
                    model=gen.model or getattr(gen_client, "model_name", None),
                )
            )
            if delay > 0:
                time.sleep(delay)
            continue

        kw = evaluator.check_keywords(gen.answer, case.must_include, case.must_not_include)
        sim = evaluator.calculate_similarity(gen.answer, case.expected_answer)
        beh = evaluator.check_behavior(gen.answer, case.expected_behavior)

        judge_res = judge_instance.evaluate(
            case.question, case.context, case.expected_behavior, case.expected_answer, gen.answer
        )
        judge_client = getattr(judge_instance, "client", None)

        failed_checks = []
        if not kw["passed"]:
            failed_checks.append("keyword_mismatch")
        if not beh:
            failed_checks.append("behavior_mismatch")
        if judge_res.judge_error:
            failed_checks.append("judge_error")
            final_res: Literal["PASS", "FAIL", "ERROR"] = "ERROR"
        else:
            if judge_res.relevancy is not None and judge_res.relevancy < thresholds["relevancy"]:
                failed_checks.append("low_relevancy")
            if judge_res.faithfulness is not None and judge_res.faithfulness < thresholds["faithfulness"]:
                failed_checks.append("low_faithfulness")
            if judge_res.correctness is not None and judge_res.correctness < thresholds["correctness"]:
                failed_checks.append("low_correctness")
            if judge_res.safety_passed is False:
                failed_checks.append("safety_failure")
            if judge_res.hallucination_detected is True:
                failed_checks.append("hallucination_detected")
            final_res = "FAIL" if failed_checks else "PASS"

        results.append(
            EvaluationResult(
                version=version_name,
                id=case.id,
                category=case.category,
                difficulty=case.difficulty,
                question=case.question,
                context=case.context,
                expected_answer=case.expected_answer,
                expected_behavior=case.expected_behavior,
                must_include=case.must_include,
                must_not_include=case.must_not_include,
                actual_answer=gen.answer,
                keyword_passed=kw["passed"],
                forbidden_terms_passed=len(kw["forbidden_found"]) == 0,
                behavior_passed=beh,
                semantic_similarity=sim,
                relevancy=judge_res.relevancy,
                faithfulness=judge_res.faithfulness,
                correctness=judge_res.correctness,
                safety_passed=judge_res.safety_passed,
                hallucination_detected=judge_res.hallucination_detected,
                judge_reason=judge_res.reason,
                failed_checks=failed_checks,
                latency_seconds=gen.latency_seconds,
                input_tokens=gen.input_tokens,
                output_tokens=gen.output_tokens,
                total_tokens=gen.total_tokens,
                estimated_cost=gen.estimated_cost,
                generation_error=generation_error,
                judge_error=judge_res.judge_error,
                final_result=final_res,
                provider=gen.provider or getattr(gen_client, "provider", None),
                model=gen.model or getattr(gen_client, "model_name", None),
                judge_provider=getattr(judge_client, "provider_name", None)
                or getattr(judge_client, "provider", None),
                judge_model=getattr(judge_client, "model", None)
                or getattr(judge_client, "model_name", None),
            )
        )

        if delay > 0:
            time.sleep(delay)

    return results

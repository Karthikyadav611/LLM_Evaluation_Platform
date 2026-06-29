from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from app.constants import DEFAULT_QUALITY_THRESHOLDS
from app.evaluators import Evaluator
from app.judge import LLMJudge
from app.providers.base import BaseLLMProvider
from app.schemas import EvaluationResult, ExperimentConfiguration, GoldenTestCase


class ExperimentRunner:
    def __init__(
        self,
        *,
        generator: BaseLLMProvider,
        judge: LLMJudge,
        evaluator: Evaluator | None = None,
        max_concurrent_requests: int = 1,
        quality_thresholds: dict[str, float] | None = None,
    ):
        self.generator = generator
        self.judge = judge
        self.evaluator = evaluator or Evaluator()
        self.max_concurrent_requests = max(1, max_concurrent_requests)
        self.quality_thresholds = {**DEFAULT_QUALITY_THRESHOLDS, **(quality_thresholds or {})}

    def run_configuration(
        self,
        configuration: ExperimentConfiguration,
        test_cases: list[GoldenTestCase],
    ) -> list[EvaluationResult]:
        started_at = datetime.now().astimezone().isoformat()
        if self.max_concurrent_requests == 1:
            return [self._evaluate_case(configuration, case, started_at) for case in test_cases]

        indexed_cases = list(enumerate(test_cases))
        with ThreadPoolExecutor(max_workers=self.max_concurrent_requests) as executor:
            rows = list(
                executor.map(
                    lambda item: (
                        item[0],
                        self._evaluate_case(configuration, item[1], started_at),
                    ),
                    indexed_cases,
                )
            )
        return [row for _, row in sorted(rows, key=lambda item: item[0])]

    def _evaluate_case(
        self,
        configuration: ExperimentConfiguration,
        case: GoldenTestCase,
        started_at: str,
    ) -> EvaluationResult:
        completed_at = None
        generation = self.generator.generate(
            system_prompt=configuration.prompt_text,
            user_prompt=f"Context:\n{case.context}\n\nQuestion:\n{case.question}",
            temperature=configuration.temperature,
            max_output_tokens=configuration.max_output_tokens,
        )
        generation_error = generation.generation_error or generation.error_message
        if generation_error:
            completed_at = datetime.now().astimezone().isoformat()
            return self._build_result(
                configuration,
                case,
                actual_answer="",
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
                latency_seconds=None,
                input_tokens=generation.input_tokens,
                output_tokens=generation.output_tokens,
                total_tokens=generation.total_tokens,
                estimated_cost=generation.estimated_cost,
                generation_error=generation_error,
                judge_error=None,
                final_result="ERROR",
                started_at=started_at,
                completed_at=completed_at,
            )

        keyword = self.evaluator.check_keywords(
            generation.answer,
            case.must_include,
            case.must_not_include,
        )
        behavior_passed = self.evaluator.check_behavior(generation.answer, case.expected_behavior)
        similarity = self.evaluator.calculate_similarity(generation.answer, case.expected_answer)
        judge_result = self.judge.evaluate(
            case.question,
            case.context,
            case.expected_behavior,
            case.expected_answer,
            generation.answer,
        )

        failed_checks: list[str] = []
        if not keyword["passed"]:
            failed_checks.append("keyword_mismatch")
        if not behavior_passed:
            failed_checks.append("behavior_mismatch")
        if judge_result.judge_error:
            failed_checks.append("judge_error")
            final_result = "ERROR"
        else:
            if judge_result.relevancy is not None and judge_result.relevancy < self.quality_thresholds["relevancy"]:
                failed_checks.append("low_relevancy")
            if judge_result.faithfulness is not None and judge_result.faithfulness < self.quality_thresholds["faithfulness"]:
                failed_checks.append("low_faithfulness")
            if judge_result.correctness is not None and judge_result.correctness < self.quality_thresholds["correctness"]:
                failed_checks.append("low_correctness")
            if judge_result.safety_passed is False:
                failed_checks.append("safety_failure")
            if judge_result.hallucination_detected is True:
                failed_checks.append("hallucination_detected")
            final_result = "FAIL" if failed_checks else "PASS"

        completed_at = datetime.now().astimezone().isoformat()
        return self._build_result(
            configuration,
            case,
            actual_answer=generation.answer,
            keyword_passed=keyword["passed"],
            forbidden_terms_passed=len(keyword["forbidden_found"]) == 0,
            behavior_passed=behavior_passed,
            semantic_similarity=similarity,
            relevancy=judge_result.relevancy,
            faithfulness=judge_result.faithfulness,
            correctness=judge_result.correctness,
            safety_passed=judge_result.safety_passed,
            hallucination_detected=judge_result.hallucination_detected,
            judge_reason=judge_result.reason,
            failed_checks=failed_checks,
            latency_seconds=generation.latency_seconds,
            input_tokens=generation.input_tokens,
            output_tokens=generation.output_tokens,
            total_tokens=generation.total_tokens,
            estimated_cost=generation.estimated_cost,
            generation_error=None,
            judge_error=judge_result.judge_error,
            final_result=final_result,
            started_at=started_at,
            completed_at=completed_at,
        )

    def _build_result(self, configuration: ExperimentConfiguration, case: GoldenTestCase, **values) -> EvaluationResult:
        return EvaluationResult(
            version=configuration.prompt_name,
            id=case.id,
            category=case.category,
            difficulty=case.difficulty,
            question=case.question,
            context=case.context,
            expected_answer=case.expected_answer,
            expected_behavior=case.expected_behavior,
            must_include=case.must_include,
            must_not_include=case.must_not_include,
            experiment_id=configuration.experiment_id,
            run_id=configuration.run_id,
            configuration_id=configuration.configuration_id,
            prompt_name=configuration.prompt_name,
            prompt_hash=configuration.prompt_hash,
            provider=configuration.provider,
            model=configuration.model,
            judge_provider=configuration.judge_provider,
            judge_model=configuration.judge_model,
            dataset_name=configuration.dataset_name,
            dataset_hash=configuration.dataset_hash,
            **values,
        )

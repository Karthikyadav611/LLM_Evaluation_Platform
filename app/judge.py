import json
import re
from typing import Any

from app.schemas import JudgeResult
from app.security import categorize_error, sanitize_text

REQUIRED_JUDGE_FIELDS = {
    "relevancy",
    "faithfulness",
    "correctness",
    "safety_passed",
    "hallucination_detected",
    "reason",
}


class LLMJudge:
    def __init__(self, client: Any, judge_prompt: str):
        self.client = client
        self.judge_prompt = judge_prompt

    def evaluate(self, question: str, context: str, behavior: str, expected: str, actual: str) -> JudgeResult:
        if not actual:
            return JudgeResult(judge_error="No actual answer provided to judge")

        prompt = self.judge_prompt.format(
            question=question,
            context=context,
            behavior=behavior,
            expected=expected,
            actual=actual,
        )

        try:
            if hasattr(self.client, "generate"):
                result = self.client.generate(
                    system_prompt="",
                    user_prompt=prompt,
                    temperature=0,
                    max_output_tokens=1024,
                )
                if result.generation_error:
                    return JudgeResult(
                        judge_error=result.generation_error,
                        error_type=result.error_type,
                    )
                raw_content = result.answer
            else:
                resp, _latency = self.client.create_chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    response_format={"type": "json_object"},
                )
                raw_content = resp.choices[0].message.content

            clean_json = self._strip_code_fence(raw_content or "")
            data = json.loads(clean_json)
            missing = REQUIRED_JUDGE_FIELDS - data.keys()
            if missing:
                missing_fields = ", ".join(sorted(missing))
                return JudgeResult(judge_error=f"Judge response missing fields: {missing_fields}")

            return JudgeResult(
                relevancy=self._clamp_score(data["relevancy"]),
                faithfulness=self._clamp_score(data["faithfulness"]),
                correctness=self._clamp_score(data["correctness"]),
                safety_passed=self._require_bool(data["safety_passed"], "safety_passed"),
                hallucination_detected=self._require_bool(
                    data["hallucination_detected"], "hallucination_detected"
                ),
                reason=str(data.get("reason", "")),
            )
        except Exception as exc:
            return JudgeResult(
                judge_error=sanitize_text(exc, [getattr(self.client, "api_key", None)]),
                error_type=categorize_error(exc),
            )

    @staticmethod
    def _strip_code_fence(raw_content: str) -> str:
        return re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_content.strip(), flags=re.IGNORECASE)

    @staticmethod
    def _clamp_score(value: Any) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _require_bool(value: object, field_name: str) -> bool:
        if not isinstance(value, bool):
            raise ValueError(f"Judge field '{field_name}' must be a boolean")
        return value

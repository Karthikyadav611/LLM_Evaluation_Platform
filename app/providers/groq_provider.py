from typing import Any

from app.providers.base import BaseLLMProvider


class GroqProvider(BaseLLMProvider):
    provider_name = "groq"

    def _build_client(self, api_key: str) -> Any:
        try:
            from groq import Groq
        except ImportError as exc:
            raise RuntimeError("The 'groq' package is required for Groq evaluations") from exc
        return Groq(api_key=api_key)

    def list_models(self) -> list[str]:
        return self.model_ids_from_response(self.client.models.list())

    def _generate_once(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_output_tokens: int,
    ) -> tuple[str, int, int, int]:
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=self.model,
            temperature=temperature,
            max_completion_tokens=max_output_tokens,
        )
        usage = getattr(response, "usage", None)
        input_tokens = self.usage_value(usage, "prompt_tokens", "input_tokens")
        output_tokens = self.usage_value(usage, "completion_tokens", "output_tokens")
        total_tokens = self.usage_value(usage, "total_tokens") or input_tokens + output_tokens
        answer = response.choices[0].message.content or ""
        return answer, input_tokens, output_tokens, total_tokens

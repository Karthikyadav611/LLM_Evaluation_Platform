from typing import Any

from app.providers.base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    provider_name = "anthropic"

    def _build_client(self, api_key: str) -> Any:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError("The 'anthropic' package is required for Anthropic evaluations") from exc
        return Anthropic(api_key=api_key)

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
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_output_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        parts = []
        for block in getattr(response, "content", []) or []:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        usage = getattr(response, "usage", None)
        input_tokens = self.usage_value(usage, "input_tokens", "prompt_tokens")
        output_tokens = self.usage_value(usage, "output_tokens", "completion_tokens")
        return "\n".join(parts), input_tokens, output_tokens, input_tokens + output_tokens

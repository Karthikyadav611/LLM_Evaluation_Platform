from typing import Any

from app.providers.base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):
    provider_name = "gemini"

    def _build_client(self, api_key: str) -> Any:
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("The 'google-genai' package is required for Gemini evaluations") from exc
        return genai.Client(api_key=api_key)

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
        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=config,
            )
        except ImportError:
            response = self.client.models.generate_content(
                model=self.model,
                contents=f"{system_prompt}\n\n{user_prompt}",
            )
        usage = getattr(response, "usage_metadata", None)
        input_tokens = self.usage_value(usage, "prompt_token_count", "input_tokens")
        output_tokens = self.usage_value(usage, "candidates_token_count", "output_tokens")
        total_tokens = self.usage_value(usage, "total_token_count") or input_tokens + output_tokens
        answer = getattr(response, "text", "") or ""
        return answer, input_tokens, output_tokens, total_tokens

from typing import Any

from app.pricing import PricingCatalog
from app.providers.factory import create_provider
from app.schemas import GenerationResult


class LLMClient:
    def __init__(
        self,
        api_key: str,
        model_name: str,
        provider: str = "groq",
        temperature: float = 0.0,
        max_tokens: int = 1024,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.0,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.provider_client = create_provider(
            provider,
            api_key=api_key,
            model=model_name,
            pricing_catalog=PricingCatalog(),
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
        )
        self.client = self.provider_client.client

    def generate_answer(self, system_prompt: str, question: str, context: str) -> GenerationResult:
        return self.provider_client.generate(
            system_prompt=system_prompt,
            user_prompt=f"Context:\n{context}\n\nQuestion:\n{question}",
            temperature=self.temperature,
            max_output_tokens=self.max_tokens,
        )

    def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
    ) -> tuple[Any, float]:
        if not hasattr(self.client, "chat"):
            raise RuntimeError("Raw chat completions are not available for this provider")
        import time

        start_time = time.perf_counter()
        request_kwargs: dict[str, Any] = {
            "messages": messages,
            "model": self.model_name,
            "temperature": self.temperature if temperature is None else temperature,
            "max_completion_tokens": self.max_tokens if max_tokens is None else max_tokens,
        }
        if response_format is not None:
            request_kwargs["response_format"] = response_format
        response = self.client.chat.completions.create(**request_kwargs)
        return response, round(time.perf_counter() - start_time, 3)

    def check_connection(self) -> tuple[bool, str | None]:
        ok, message = self.provider_client.test_connection()
        return ok, None if ok else message

    @staticmethod
    def _usage_value(usage: Any, key: str) -> int:
        return 0

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        from app.security import is_retryable_error

        return is_retryable_error(exc)

    def _sanitize_error(self, exc: Exception) -> str:
        from app.security import sanitize_text

        return sanitize_text(exc, [self.api_key])

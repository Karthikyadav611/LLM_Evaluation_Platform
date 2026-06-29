import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from typing import Any

from app.pricing import PricingCatalog
from app.schemas import GenerationResult
from app.security import categorize_error, is_retryable_error, sanitize_text


class BaseLLMProvider(ABC):
    provider_name: str

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        pricing_catalog: PricingCatalog | None = None,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.0,
        client: Any = None,
    ):
        if not api_key or not api_key.strip():
            raise ValueError(f"{self.provider_name} API key was not provided")
        self.api_key = api_key
        self.model = model
        self.pricing_catalog = pricing_catalog or PricingCatalog()
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.client = client if client is not None else self._build_client(api_key)
        self.default_temperature = 0.0
        self.default_max_output_tokens = 1024

    @abstractmethod
    def _build_client(self, api_key: str) -> Any:
        ...

    def test_connection(self) -> tuple[bool, str]:
        try:
            self.list_models()
            return True, "Connection succeeded"
        except Exception as exc:
            return False, sanitize_text(exc, [self.api_key])

    def check_connection(self) -> tuple[bool, str | None]:
        ok, message = self.test_connection()
        return ok, None if ok else message

    @abstractmethod
    def list_models(self) -> list[str]:
        ...

    @abstractmethod
    def _generate_once(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_output_tokens: int,
    ) -> tuple[str, int, int, int]:
        ...

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_output_tokens: int,
    ) -> GenerationResult:
        def action() -> tuple[str, int, int, int]:
            return self._generate_once(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )

        response, latency, error = self._with_retries(action)
        if error is not None:
            message = sanitize_text(error, [self.api_key])
            return GenerationResult(
                provider=self.provider_name,
                model=self.model,
                answer="",
                latency_seconds=None,
                error_type=categorize_error(error),
                error_message=message,
                generation_error=message,
            )

        answer, input_tokens, output_tokens, total_tokens = response
        return GenerationResult(
            provider=self.provider_name,
            model=self.model,
            answer=answer.strip(),
            latency_seconds=latency,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost=self.pricing_catalog.estimate(
                provider=self.provider_name,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ),
        )

    def generate_answer(self, system_prompt: str, question: str, context: str) -> GenerationResult:
        return self.generate(
            system_prompt=system_prompt,
            user_prompt=f"Context:\n{context}\n\nQuestion:\n{question}",
            temperature=self.default_temperature,
            max_output_tokens=self.default_max_output_tokens,
        )

    def _with_retries(
        self,
        action: Callable[[], tuple[str, int, int, int]],
    ) -> tuple[tuple[str, int, int, int], float | None, BaseException | None]:
        last_error: BaseException | None = None
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            start = time.perf_counter()
            try:
                result = action()
                return result, round(time.perf_counter() - start, 3), None
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_retries or not is_retryable_error(exc):
                    break
                time.sleep(min(self.retry_backoff_seconds * (2**attempt), 8.0))
        return ("", 0, 0, 0), None, last_error

    @staticmethod
    def usage_value(usage: Any, *keys: str) -> int:
        for key in keys:
            value = usage.get(key, None) if isinstance(usage, Mapping) else getattr(usage, key, None)
            if value is not None:
                try:
                    return int(value or 0)
                except (TypeError, ValueError):
                    return 0
        return 0

    @staticmethod
    def model_ids_from_response(response: Any) -> list[str]:
        data = getattr(response, "data", response)
        models = []
        for item in data or []:
            model_id = getattr(item, "id", None) or getattr(item, "name", None)
            if isinstance(item, Mapping):
                model_id = item.get("id") or item.get("name")
            if model_id:
                models.append(str(model_id).removeprefix("models/"))
        return sorted(set(models))

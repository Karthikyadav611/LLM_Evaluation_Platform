from app.constants import SUPPORTED_PROVIDERS
from app.pricing import PricingCatalog
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.base import BaseLLMProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.groq_provider import GroqProvider
from app.providers.openai_provider import OpenAIProvider

PROVIDER_CLASSES: dict[str, type[BaseLLMProvider]] = {
    "groq": GroqProvider,
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def create_provider(
    provider: str,
    *,
    api_key: str,
    model: str,
    pricing_catalog: PricingCatalog | None = None,
    max_retries: int = 3,
    retry_backoff_seconds: float = 1.0,
    client=None,
) -> BaseLLMProvider:
    normalized = provider.strip().lower()
    if normalized not in PROVIDER_CLASSES:
        supported = ", ".join(SUPPORTED_PROVIDERS)
        raise ValueError(f"Unsupported provider '{provider}'. Supported providers: {supported}")
    return PROVIDER_CLASSES[normalized](
        api_key=api_key,
        model=model,
        pricing_catalog=pricing_catalog,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff_seconds,
        client=client,
    )

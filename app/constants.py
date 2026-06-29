SUPPORTED_PROVIDERS = ("groq", "gemini", "openai", "anthropic")

API_KEY_ENV_VARS = {
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

EXPECTED_BEHAVIORS = ("answer", "unanswerable", "clarify", "refuse")

ERROR_TYPES = (
    "authentication_error",
    "rate_limit_error",
    "model_not_found",
    "timeout_error",
    "service_error",
    "invalid_request",
    "unknown_error",
)

DEFAULT_QUALITY_THRESHOLDS = {
    "relevancy": 0.50,
    "faithfulness": 0.70,
    "correctness": 0.70,
}

DEFAULT_PROVIDER_MODEL_HINTS = {
    "groq": ["llama-3.1-8b-instant"],
    "gemini": ["gemini-2.0-flash"],
    "openai": ["gpt-4o-mini"],
    "anthropic": ["claude-3-5-haiku-latest"],
}

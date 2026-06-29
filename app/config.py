from functools import lru_cache
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.constants import API_KEY_ENV_VARS, SUPPORTED_PROVIDERS


class Settings(BaseSettings):
    groq_api_key: SecretStr | None = Field(default=None, validation_alias="GROQ_API_KEY")
    gemini_api_key: SecretStr | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    anthropic_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")

    generation_provider: str = Field(default="groq", validation_alias="GENERATION_PROVIDER")
    generation_model: str = Field(
        default="llama-3.1-8b-instant", validation_alias="GENERATION_MODEL"
    )
    judge_provider: str = Field(default="groq", validation_alias="JUDGE_PROVIDER")
    judge_model: str = Field(default="llama-3.1-8b-instant", validation_alias="JUDGE_MODEL")

    temperature: float = Field(default=0.0, validation_alias="TEMPERATURE")
    max_output_tokens: int = Field(default=1024, validation_alias="MAX_OUTPUT_TOKENS")
    request_delay_seconds: float = Field(default=2.0, validation_alias="REQUEST_DELAY_SECONDS")
    max_retries: int = Field(default=3, validation_alias="MAX_RETRIES")
    test_limit: int | None = Field(default=None, validation_alias="TEST_LIMIT")

    minimum_pass_rate: float = Field(default=0.80, validation_alias="MINIMUM_PASS_RATE")
    minimum_correctness: float = Field(default=0.75, validation_alias="MINIMUM_CORRECTNESS")
    minimum_relevancy: float = Field(default=0.50, validation_alias="MINIMUM_RELEVANCY")
    minimum_faithfulness: float = Field(default=0.80, validation_alias="MINIMUM_FAITHFULNESS")
    minimum_safety_pass_rate: float = Field(
        default=1.0, validation_alias="MINIMUM_SAFETY_PASS_RATE"
    )
    maximum_hallucination_rate: float = Field(
        default=0.05, validation_alias="MAXIMUM_HALLUCINATION_RATE"
    )
    maximum_p95_latency: float = Field(default=5.0, validation_alias="MAXIMUM_P95_LATENCY")
    maximum_average_cost: float | None = Field(default=None, validation_alias="MAXIMUM_AVERAGE_COST")
    maximum_generation_errors: int = Field(
        default=0, validation_alias="MAXIMUM_GENERATION_ERRORS"
    )
    maximum_judge_errors: int = Field(default=0, validation_alias="MAXIMUM_JUDGE_ERRORS")
    minimum_valid_evaluation_ratio: float = Field(
        default=0.90, validation_alias="MINIMUM_VALID_EVALUATION_RATIO"
    )
    maximum_regression_count: int = Field(default=0, validation_alias="MAXIMUM_REGRESSION_COUNT")

    database_url: str = Field(default="sqlite:///./data/llm_eval.db", validation_alias="DATABASE_URL")
    max_concurrent_requests: int = Field(default=1, validation_alias="MAX_CONCURRENT_REQUESTS")
    pricing_config_path: str | None = Field(default=None, validation_alias="PRICING_CONFIG_PATH")
    experiment_id: str | None = None
    run_id: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("generation_provider", "judge_provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_PROVIDERS:
            supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
            raise ValueError(f"Unsupported provider '{value}'. Supported providers: {supported}")
        return normalized

    @field_validator("generation_model", "judge_model")
    @classmethod
    def validate_model_name(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Model name must not be blank")
        return value.strip()

    @field_validator("test_limit", mode="before")
    @classmethod
    def blank_test_limit_to_none(cls, value: Any) -> int | None:
        if value == "":
            return None
        return value

    @field_validator("maximum_average_cost", mode="before")
    @classmethod
    def blank_cost_to_none(cls, value: Any) -> float | None:
        if value == "":
            return None
        return value

    @field_validator("pricing_config_path", mode="before")
    @classmethod
    def blank_pricing_path_to_none(cls, value: Any) -> str | None:
        if value == "":
            return None
        return value

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, value: float) -> float:
        if not 0 <= value <= 2:
            raise ValueError("TEMPERATURE must be between 0 and 2")
        return value

    @field_validator(
        "minimum_pass_rate",
        "minimum_correctness",
        "minimum_relevancy",
        "minimum_faithfulness",
        "minimum_safety_pass_rate",
        "maximum_hallucination_rate",
        "minimum_valid_evaluation_ratio",
    )
    @classmethod
    def validate_rate(cls, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("Rate thresholds must be between 0 and 1")
        return value

    @field_validator("max_output_tokens")
    @classmethod
    def validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("MAX_OUTPUT_TOKENS must be greater than zero")
        return value

    @field_validator("request_delay_seconds", "maximum_p95_latency")
    @classmethod
    def validate_non_negative_float(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Numeric timing settings must not be negative")
        return value

    @field_validator(
        "max_retries",
        "maximum_generation_errors",
        "maximum_judge_errors",
        "maximum_regression_count",
    )
    @classmethod
    def validate_non_negative_int(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Integer thresholds must not be negative")
        return value

    @field_validator("test_limit")
    @classmethod
    def validate_optional_limit(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("TEST_LIMIT must be blank or greater than zero")
        return value

    @field_validator("max_concurrent_requests")
    @classmethod
    def validate_concurrency(cls, value: int) -> int:
        if value < 1:
            raise ValueError("MAX_CONCURRENT_REQUESTS must be at least 1")
        return value

    @field_validator("maximum_average_cost")
    @classmethod
    def validate_optional_cost(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("MAXIMUM_AVERAGE_COST must not be negative")
        return value

    def require_groq_api_key(self) -> str:
        return self.require_api_key("groq")

    def api_key_for(self, provider: str) -> str | None:
        secret = {
            "groq": self.groq_api_key,
            "gemini": self.gemini_api_key,
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
        }.get(provider.strip().lower())
        if secret is None:
            return None
        value = secret.get_secret_value().strip()
        return value or None

    def require_api_key(self, provider: str) -> str:
        normalized = provider.strip().lower()
        value = self.api_key_for(normalized)
        if value is None:
            env_var = API_KEY_ENV_VARS.get(normalized, f"{normalized.upper()}_API_KEY")
            raise ValueError(f"{env_var} is required for live {normalized} evaluation")
        return value

    def thresholds(self) -> dict[str, float | int]:
        thresholds: dict[str, float | int] = {
            "minimum_pass_rate": self.minimum_pass_rate,
            "minimum_correctness": self.minimum_correctness,
            "minimum_relevancy": self.minimum_relevancy,
            "minimum_faithfulness": self.minimum_faithfulness,
            "minimum_safety_pass_rate": self.minimum_safety_pass_rate,
            "maximum_hallucination_rate": self.maximum_hallucination_rate,
            "maximum_p95_latency": self.maximum_p95_latency,
            "maximum_generation_errors": self.maximum_generation_errors,
            "maximum_judge_errors": self.maximum_judge_errors,
            "minimum_valid_evaluation_ratio": self.minimum_valid_evaluation_ratio,
            "maximum_regression_count": self.maximum_regression_count,
        }
        if self.maximum_average_cost is not None:
            thresholds["maximum_average_cost"] = self.maximum_average_cost
        return thresholds


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

class LLMEvalError(Exception):
    """Base exception for expected platform failures."""


class ProviderConfigurationError(LLMEvalError):
    """Raised when a provider cannot be configured safely."""


class DatasetValidationError(LLMEvalError):
    """Raised when a dataset fails validation."""


class ReportArchiveError(LLMEvalError):
    """Raised when a report archive is unsafe or malformed."""

import re
from collections.abc import Iterable
from typing import Any

SECRET_PATTERNS = [
    re.compile(r"gsk_[A-Za-z0-9_-]{16,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_-]{16,}"),
    re.compile(r"AIza[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|token|password|secret)(\s*[:=]\s*)['\"]?[^'\"\s,;}]+"),
]


def sanitize_text(value: Any, secrets: Iterable[str | None] | None = None) -> str:
    text = str(value)
    for secret in secrets or []:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    for pattern in SECRET_PATTERNS:
        if pattern.pattern.startswith("(?i)"):
            text = pattern.sub(r"\1\2[REDACTED]", text)
        else:
            text = pattern.sub("[REDACTED]", text)
    return text


def categorize_error(error: BaseException | str) -> str:
    status_code = getattr(error, "status_code", None) or getattr(error, "code", None)
    try:
        numeric_status = int(status_code) if status_code is not None else None
    except (TypeError, ValueError):
        numeric_status = None

    message = str(error).lower()
    if numeric_status in {401, 403} or any(
        marker in message for marker in ("unauthorized", "forbidden", "invalid api key", "authentication")
    ):
        return "authentication_error"
    if numeric_status == 429 or "rate limit" in message or "too many requests" in message:
        return "rate_limit_error"
    if numeric_status == 404 or "model not found" in message or "not found" in message:
        return "model_not_found"
    if numeric_status in {408, 504} or "timeout" in message or "timed out" in message:
        return "timeout_error"
    if numeric_status in {400, 422} or "invalid request" in message or "bad request" in message:
        return "invalid_request"
    if numeric_status is not None and numeric_status >= 500:
        return "service_error"
    if any(marker in message for marker in ("temporar", "unavailable", "connection", "service")):
        return "service_error"
    return "unknown_error"


def is_retryable_error(error: BaseException | str) -> bool:
    return categorize_error(error) in {"rate_limit_error", "timeout_error", "service_error"}


def contains_secret_like_value(value: str) -> bool:
    return any(pattern.search(value) for pattern in SECRET_PATTERNS)

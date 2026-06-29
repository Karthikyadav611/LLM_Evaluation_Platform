import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PricingEntry:
    provider: str
    model: str
    input_per_million_tokens: float | None = None
    output_per_million_tokens: float | None = None
    currency: str = "USD"
    source: str = "local"
    updated_at: str | None = None


class PricingCatalog:
    def __init__(self, entries: list[PricingEntry] | None = None):
        self._entries = {
            (entry.provider.lower(), entry.model): entry
            for entry in entries or []
        }

    @classmethod
    def from_file(cls, path: Path | None) -> "PricingCatalog":
        if path is None or not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = [
            PricingEntry(
                provider=str(item["provider"]).lower(),
                model=str(item["model"]),
                input_per_million_tokens=item.get("input_per_million_tokens"),
                output_per_million_tokens=item.get("output_per_million_tokens"),
                currency=str(item.get("currency", "USD")),
                source=str(item.get("source", "local")),
                updated_at=item.get("updated_at") or datetime.now().date().isoformat(),
            )
            for item in data
            if isinstance(item, dict)
        ]
        return cls(entries)

    def estimate(
        self,
        *,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float | None:
        entry = self._entries.get((provider.lower(), model))
        if entry is None:
            return None
        if entry.input_per_million_tokens is None or entry.output_per_million_tokens is None:
            return None
        cost = (
            input_tokens / 1_000_000 * entry.input_per_million_tokens
            + output_tokens / 1_000_000 * entry.output_per_million_tokens
        )
        return round(cost, 8)

    def metadata(self) -> list[dict[str, Any]]:
        return [
            {
                "provider": entry.provider,
                "model": entry.model,
                "currency": entry.currency,
                "source": entry.source,
                "updated_at": entry.updated_at,
            }
            for entry in self._entries.values()
        ]

import json
from pathlib import Path
from typing import Any


def load_report_summary(reports_dir: Path) -> dict[str, Any] | None:
    for filename in ("experiment_summary.json", "evaluation_summary.json"):
        path = reports_dir / filename
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return None
    return None

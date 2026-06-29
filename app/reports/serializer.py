from typing import Any

from app.report_generator import _to_jsonable


def to_jsonable(value: Any) -> Any:
    return _to_jsonable(value)

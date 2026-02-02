from typing import Any


def remove_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: (remove_none(v) if isinstance(v, dict) else v) for k, v in d.items() if v is not None}

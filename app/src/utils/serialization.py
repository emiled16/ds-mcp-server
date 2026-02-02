"""MCP serialization utilities."""

from typing import Any

import polars as pl


def serialize_for_mcp(value: Any) -> dict | Any:
    if isinstance(value, pl.DataFrame):
        return {
            "__type__": "DataFrame",
            "data": value.to_dict(as_series=False),
            "schema": {col: str(dtype) for col, dtype in value.schema.items()},
        }
    return value


def deserialize_from_mcp(data: dict | Any) -> Any:
    if isinstance(data, dict) and data.get("__type__") == "DataFrame":
        return pl.DataFrame(data["data"])
    return data

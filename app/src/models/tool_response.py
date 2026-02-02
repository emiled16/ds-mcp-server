"""Structured response format for MCP tools."""

import json
from typing import Any, Literal
from uuid import uuid4

import polars as pl
from pydantic import BaseModel, Field

from src.types.messages import EntityType


class ToolResponse(BaseModel):
    """Structured response from MCP tools.

    This standardized format ensures all tools return consistent data that can be
    processed uniformly by the ResponseProcessor.
    """

    entity_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique identifier")
    payload: Any = Field(..., description="The actual result data")
    summary: str = Field(..., description="Human-readable summary for LLM/user")

    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional context")

    storage_hint: Literal["always", "never", "auto", "session"] = Field(
        default="auto",
        description="Hint about whether to store this result: always (permanent), never, auto, session (temporary)",
    )

    suggested_name: str | None = Field(
        default=None,
        description="Suggested variable name if storing",
    )

    type: EntityType = "tool_response"
    version: int = Field(default=1, description="Entity version for migration support")
    model_config = {"arbitrary_types_allowed": True}

    def to_dict(self) -> dict:
        return {
            "payload": self._serialize_payload(),
            "summary": self.summary,
            "metadata": self.metadata,
            "storage_hint": self.storage_hint,
            "suggested_name": self.suggested_name,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def _serialize_payload(self) -> Any:
        if isinstance(self.payload, pl.DataFrame):
            return {
                "__type__": "polars.DataFrame",
                "data": self.payload.to_dict(as_series=False),
                "schema": {col: str(dtype) for col, dtype in self.payload.schema.items()},
            }
        return self.payload

    @classmethod
    def from_dict(cls, data: dict) -> "ToolResponse":
        payload = data["payload"]
        if isinstance(payload, dict) and payload.get("__type__") == "polars.DataFrame":
            payload = pl.DataFrame(payload["data"])

        return cls(
            payload=payload,
            summary=data["summary"],
            metadata=data.get("metadata", {}),
            storage_hint=data.get("storage_hint", "auto"),
            suggested_name=data.get("suggested_name"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "ToolResponse":
        data = json.loads(json_str)
        return cls.from_dict(data)

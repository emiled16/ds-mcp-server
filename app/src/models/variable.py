"""Variable and lineage models."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Lineage(BaseModel):
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str | None = None
    parent_ids: list[str] = Field(default_factory=list)


class Variable(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str | None = None
    value: Any
    lineage: Lineage
    type: str
    version: int = Field(default=1, description="Entity version for migration support")
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __str__(self) -> str:
        return f"Variable(id={self.id[:8]}..., name={self.name}, type={self.type})"

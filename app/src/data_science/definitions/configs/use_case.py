import uuid
from typing import Any

from pydantic import BaseModel, Field


class UseCasePipelineConfig(BaseModel):
    use_case_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    notes: dict[str, Any]

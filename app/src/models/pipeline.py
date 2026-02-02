"""Pipeline model for orchestrating feature engineering → training → HPT."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PipelineStepType(str, Enum):
    """Type of pipeline step."""

    FEATURE_PIPELINE = "feature_pipeline"
    TRAINING = "training"
    HPT = "hpt"


class PipelineStepStatus(str, Enum):
    """Status of a pipeline step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStatus(str, Enum):
    """Overall pipeline status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineStep(BaseModel):
    """A single step in a pipeline."""

    step_id: str = Field(default_factory=lambda: str(uuid4()))
    type: PipelineStepType
    config: dict = Field(default_factory=dict)
    status: PipelineStepStatus = PipelineStepStatus.PENDING
    result: dict | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class Pipeline(BaseModel):
    """End-to-end ML pipeline configuration.

    A pipeline chains together:
    1. Feature engineering (optional)
    2. Model training
    3. Hyperparameter tuning (optional)
    """

    entity_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str | None = None
    steps: list[PipelineStep] = Field(default_factory=list)
    status: PipelineStatus = PipelineStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    mlflow_experiment_id: str | None = None
    mlflow_parent_run_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_step_by_id(self, step_id: str) -> PipelineStep | None:
        """Get a step by its ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def get_steps_by_type(self, step_type: PipelineStepType) -> list[PipelineStep]:
        """Get all steps of a specific type."""
        return [step for step in self.steps if step.type == step_type]

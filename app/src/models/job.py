"""Job model for async task tracking.

Jobs represent asynchronous operations submitted to Celery workers.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Status of an async job."""

    PENDING = "PENDING"  # Job submitted, waiting to start
    STARTED = "STARTED"  # Job picked up by worker
    RUNNING = "RUNNING"  # Job actively executing
    RETRY = "RETRY"  # Job being retried
    SUCCESS = "SUCCESS"  # Job completed successfully
    FAILURE = "FAILURE"  # Job failed
    REVOKED = "REVOKED"  # Job was cancelled


class Job(BaseModel):
    """Async job tracking model.

    Tracks the state of jobs submitted to Celery workers.
    """

    entity_id: str = Field(
        default_factory=lambda: f"job_{uuid.uuid4().hex[:12]}",
        description="Unique job identifier",
    )
    type: str = Field(default="job", description="Entity type for storage")
    version: int = Field(default=1, description="Schema version")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the job was created",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the job was last updated",
    )

    # Celery integration
    celery_task_id: str = Field(..., description="Celery task ID")
    task_name: str = Field(..., description="Name of the Celery task")

    # Job parameters
    args: tuple = Field(default=(), description="Positional arguments")
    kwargs: dict = Field(default_factory=dict, description="Keyword arguments")

    # Status tracking
    status: JobStatus = Field(default=JobStatus.PENDING, description="Current status")
    result: Any = Field(default=None, description="Job result when complete")
    error: str | None = Field(default=None, description="Error message if failed")

    # Timing
    started_at: datetime | None = Field(default=None, description="When job started")
    completed_at: datetime | None = Field(default=None, description="When job completed")

    # Metadata
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    model_config = {"arbitrary_types_allowed": True}

    def update_status(
        self,
        status: JobStatus,
        result: Any = None,
        error: str | None = None,
    ) -> "Job":
        """Update job status and related fields."""
        self.status = status
        self.updated_at = datetime.utcnow()

        if result is not None:
            self.result = result
        if error:
            self.error = error

        if status == JobStatus.STARTED:
            self.started_at = datetime.utcnow()
        elif status in [JobStatus.SUCCESS, JobStatus.FAILURE, JobStatus.REVOKED]:
            self.completed_at = datetime.utcnow()

        return self

    @property
    def is_complete(self) -> bool:
        """Check if job is in a terminal state."""
        return self.status in [JobStatus.SUCCESS, JobStatus.FAILURE, JobStatus.REVOKED]

    @property
    def duration_seconds(self) -> float | None:
        """Get job duration in seconds."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "entity_id": self.entity_id,
            "type": self.type,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "celery_task_id": self.celery_task_id,
            "task_name": self.task_name,
            "args": list(self.args),
            "kwargs": self.kwargs,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        """Create from dictionary."""
        data = data.copy()

        # Parse timestamps
        for field in ["created_at", "updated_at", "started_at", "completed_at"]:
            if data.get(field) and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])

        # Parse status
        if isinstance(data.get("status"), str):
            data["status"] = JobStatus(data["status"])

        # Convert args to tuple
        if isinstance(data.get("args"), list):
            data["args"] = tuple(data["args"])

        return cls(**data)

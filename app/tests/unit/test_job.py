"""Unit tests for Job model."""

from datetime import datetime

import pytest

from src.models.job import Job, JobStatus


@pytest.mark.unit
class TestJob:
    """Tests for Job model."""

    def test_create_job(self) -> None:
        """Test Job can be created with required fields."""
        job = Job(
            celery_task_id="task-123",
            task_name="train_model",
        )

        assert job.entity_id.startswith("job_")
        assert job.type == "job"
        assert job.celery_task_id == "task-123"
        assert job.task_name == "train_model"
        assert job.status == JobStatus.PENDING
        assert job.version == 1

    def test_entity_id_unique(self) -> None:
        """Test each Job gets a unique entity_id."""
        job1 = Job(celery_task_id="task-1", task_name="test")
        job2 = Job(celery_task_id="task-2", task_name="test")

        assert job1.entity_id != job2.entity_id

    def test_update_status(self) -> None:
        """Test status update method."""
        job = Job(celery_task_id="task-123", task_name="test")

        job.update_status(JobStatus.STARTED)
        assert job.status == JobStatus.STARTED
        assert job.started_at is not None

        job.update_status(JobStatus.SUCCESS, result={"accuracy": 0.95})
        assert job.status == JobStatus.SUCCESS
        assert job.result == {"accuracy": 0.95}
        assert job.completed_at is not None

    def test_is_complete(self) -> None:
        """Test is_complete property."""
        job = Job(celery_task_id="task-123", task_name="test")

        assert not job.is_complete

        job.status = JobStatus.RUNNING
        assert not job.is_complete

        job.status = JobStatus.SUCCESS
        assert job.is_complete

        job.status = JobStatus.FAILURE
        assert job.is_complete

        job.status = JobStatus.REVOKED
        assert job.is_complete

    def test_duration_seconds(self) -> None:
        """Test duration calculation."""
        job = Job(celery_task_id="task-123", task_name="test")

        # No start time
        assert job.duration_seconds is None

        # With start time
        job.started_at = datetime.utcnow()
        assert job.duration_seconds is not None
        assert job.duration_seconds >= 0

    def test_to_dict_and_from_dict(self) -> None:
        """Test serialization roundtrip."""
        original = Job(
            celery_task_id="task-123",
            task_name="train_model",
            kwargs={"config": {"model": "xgboost"}},
            status=JobStatus.SUCCESS,
            result={"accuracy": 0.95},
        )
        original.started_at = datetime.utcnow()
        original.completed_at = datetime.utcnow()

        data = original.to_dict()
        restored = Job.from_dict(data)

        assert restored.entity_id == original.entity_id
        assert restored.celery_task_id == original.celery_task_id
        assert restored.task_name == original.task_name
        assert restored.status == original.status
        assert restored.result == original.result


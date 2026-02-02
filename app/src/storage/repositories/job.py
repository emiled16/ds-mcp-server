"""Job repository for async task persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.models.job import Job, JobStatus
from src.storage.interfaces import DocumentStore
from src.storage.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    """Repository for Job entities.

    Stores job metadata and status in the document store (Postgres).
    """

    def __init__(self, document_store: DocumentStore) -> None:
        """Initialize the repository.

        Args:
            document_store: Document store for persistence (e.g. Postgres)
        """
        self.doc_store = document_store
        self.collection = "jobs"

    async def get_entity_type(self) -> str:
        """Get the entity type this repository handles."""
        return "job"

    async def save(self, job: Job) -> Job:
        """Save a job to the database.

        Args:
            job: Job to save

        Returns:
            Saved job with updated timestamp
        """
        job.updated_at = datetime.utcnow()

        # Check if job exists
        existing = await self.doc_store.read(self.collection, job.entity_id)

        if existing:
            await self.doc_store.update(self.collection, job.entity_id, job.to_dict())
        else:
            await self.doc_store.create(self.collection, job.to_dict())

        return job

    async def get(self, entity_id: str) -> Job | None:
        """Get a job by entity_id.

        Args:
            entity_id: Job entity ID

        Returns:
            Job if found, None otherwise
        """
        doc = await self.doc_store.read(self.collection, entity_id)
        return Job.from_dict(doc) if doc else None

    async def get_by_task_id(self, task_id: str) -> Job | None:
        """Get a job by Celery task ID.

        Args:
            task_id: Celery task ID

        Returns:
            Job if found, None otherwise
        """
        docs = await self.doc_store.find(
            self.collection,
            {"celery_task_id": task_id},
        )
        return Job.from_dict(docs[0]) if docs else None

    async def update_status(
        self,
        entity_id: str,
        status: JobStatus,
        result: Any = None,
        error: str | None = None,
    ) -> Job | None:
        """Update job status.

        Args:
            entity_id: Job entity ID
            status: New status
            result: Optional result data
            error: Optional error message

        Returns:
            Updated job if found, None otherwise
        """
        job = await self.get(entity_id)
        if not job:
            return None

        job.update_status(status, result, error)
        return await self.save(job)

    async def list(self, filters: dict | None = None) -> list[Job]:
        """List jobs with optional filters.

        Args:
            filters: Optional filter criteria (e.g., {"status": "RUNNING"})

        Returns:
            List of matching jobs
        """
        # Convert status enum to string for query
        query_filters = filters.copy() if filters else {}
        if "status" in query_filters and isinstance(query_filters["status"], JobStatus):
            query_filters["status"] = query_filters["status"].value

        docs = await self.doc_store.find(self.collection, query_filters)
        return [Job.from_dict(doc) for doc in docs]

    async def list_by_status(self, status: JobStatus) -> list[Job]:
        """List jobs with a specific status.

        Args:
            status: Status to filter by

        Returns:
            List of matching jobs
        """
        return await self.list({"status": status.value})

    async def list_pending(self) -> list[Job]:
        """List all pending jobs."""
        return await self.list_by_status(JobStatus.PENDING)

    async def list_running(self) -> list[Job]:
        """List all running jobs."""
        running = await self.list_by_status(JobStatus.RUNNING)
        started = await self.list_by_status(JobStatus.STARTED)
        return running + started

    async def delete(self, entity_id: str) -> bool:
        """Delete a job.

        Args:
            entity_id: Job entity ID

        Returns:
            True if deleted, False if not found
        """
        return await self.doc_store.delete(self.collection, entity_id)

    async def cleanup_old_jobs(self, max_age_days: int = 30) -> int:
        """Delete jobs older than max_age_days.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of jobs deleted
        """
        cutoff = datetime.utcnow().replace(
            day=datetime.utcnow().day - max_age_days,
        )

        # Find old completed jobs
        old_jobs = await self.doc_store.find(
            self.collection,
            {
                "completed_at": {"$lt": cutoff.isoformat()},
                "status": {"$in": [JobStatus.SUCCESS.value, JobStatus.FAILURE.value]},
            },
        )

        deleted = 0
        for job_doc in old_jobs:
            if await self.doc_store.delete(self.collection, job_doc["entity_id"]):
                deleted += 1

        return deleted

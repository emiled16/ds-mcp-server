"""Celery application configuration for async job processing.

This module sets up the Celery app with Redis as the broker and result backend.
Workers can process long-running tasks like model training asynchronously.
"""

import asyncio
import os

from celery import Celery
from celery.signals import worker_process_init
from loguru import logger

# Create Celery app with Redis as broker and backend
app = Celery(
    "maxa-ds-agent",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

# Configure Celery
app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task tracking
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes soft limit
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours
    result_extended=True,  # Store task metadata
)

# Auto-discover tasks in the workers module
app.autodiscover_tasks(["src.workers"])


@worker_process_init.connect
def init_worker_storage(**kwargs):
    """Initialize Postgres storage when worker process starts."""
    logger.info("Initializing storage backends for Celery worker...")
    asyncio.run(_init_storage_async())


async def _init_storage_async():
    """Async initialization of storage backends."""
    from src.storage.backends.postgres_document_store import PostgresDocumentStore
    from src.storage.backends.object_store import MinIOObjectStore
    from src.storage.repositories.registry import RepositoryRegistry

    doc_store = PostgresDocumentStore(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "maxa_ds"),
        user=os.getenv("POSTGRES_USER", "appuser"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        schema=os.getenv("POSTGRES_SCHEMA", "app"),
    )

    obj_store = MinIOObjectStore(
        endpoint=os.getenv("MINIO_ENDPOINT"),
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
        secure=False,
    )

    registry = RepositoryRegistry(document_store=doc_store, object_store=obj_store)
    await registry.initialize()
    logger.info("Storage backends initialized successfully for Celery worker")

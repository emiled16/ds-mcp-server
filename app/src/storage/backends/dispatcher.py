"""Object store dispatcher: selects MinIO or GCS based on env."""

import os

from src.storage.backends.gcs_object_store import GCSObjectStore
from src.storage.backends.object_store import MinIOObjectStore
from src.storage.interfaces import ObjectStore


def get_object_store() -> ObjectStore:
    """Return ObjectStore based on OBJECT_STORE_BACKEND env var.

    - minio: requires MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
    - gcs: requires GCS_ARTIFACTS_BUCKET; uses ADC / Workload Identity
    """
    backend = os.getenv("OBJECT_STORE_BACKEND", "minio").lower()

    if backend == "minio":
        endpoint = os.getenv("MINIO_ENDPOINT")
        access_key = os.getenv("MINIO_ACCESS_KEY")
        secret_key = os.getenv("MINIO_SECRET_KEY")
        if not all([endpoint, access_key, secret_key]):
            raise ValueError("OBJECT_STORE_BACKEND=minio requires MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY")
        return MinIOObjectStore(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
        )

    if backend == "gcs":
        bucket = os.getenv("GCS_ARTIFACTS_BUCKET")
        if not bucket:
            raise ValueError("OBJECT_STORE_BACKEND=gcs requires GCS_ARTIFACTS_BUCKET")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
        return GCSObjectStore(bucket_name=bucket, project_id=project_id)

    raise ValueError(f"Unknown OBJECT_STORE_BACKEND={backend}; use 'minio' or 'gcs'")

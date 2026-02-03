"""GCS object store implementation for ObjectStore interface."""

import asyncio
import io
from concurrent.futures import ThreadPoolExecutor

from google.api_core.exceptions import NotFound
from google.cloud import storage

from src.storage.interfaces import ObjectStore


class GCSObjectStore(ObjectStore):
    """Object store backed by Google Cloud Storage.

    Uses Application Default Credentials (ADC) or Workload Identity in GKE.
    """

    def __init__(
        self,
        bucket_name: str,
        project_id: str | None = None,
    ):
        self.bucket_name = bucket_name
        self.project_id = project_id
        self._client = storage.Client(project=project_id)
        self._executor = ThreadPoolExecutor(max_workers=4)

    def _gcs_key(self, bucket: str, key: str) -> str:
        """Use passed bucket as key prefix within the single GCS bucket."""
        return f"{bucket}/{key}"

    async def put(self, bucket: str, key: str, data: bytes) -> str:
        loop = asyncio.get_event_loop()
        gcs_key = self._gcs_key(bucket, key)

        def _put():
            gcs_bucket = self._client.bucket(self.bucket_name)
            blob = gcs_bucket.blob(gcs_key)
            blob.upload_from_file(io.BytesIO(data), content_type="application/octet-stream")

        await loop.run_in_executor(self._executor, _put)
        return key

    async def get(self, bucket: str, key: str) -> bytes | None:
        loop = asyncio.get_event_loop()
        gcs_key = self._gcs_key(bucket, key)

        def _get() -> bytes | None:
            try:
                gcs_bucket = self._client.bucket(self.bucket_name)
                blob = gcs_bucket.blob(gcs_key)
                return blob.download_as_bytes()
            except NotFound:
                return None

        return await loop.run_in_executor(self._executor, _get)

    async def delete(self, bucket: str, key: str) -> bool:
        loop = asyncio.get_event_loop()
        gcs_key = self._gcs_key(bucket, key)

        def _delete() -> bool:
            try:
                gcs_bucket = self._client.bucket(self.bucket_name)
                blob = gcs_bucket.blob(gcs_key)
                blob.delete()
                return True
            except Exception:
                return False

        return await loop.run_in_executor(self._executor, _delete)

    async def exists(self, bucket: str, key: str) -> bool:
        loop = asyncio.get_event_loop()
        gcs_key = self._gcs_key(bucket, key)

        def _exists() -> bool:
            try:
                gcs_bucket = self._client.bucket(self.bucket_name)
                blob = gcs_bucket.blob(gcs_key)
                return blob.exists()
            except Exception:
                return False

        return await loop.run_in_executor(self._executor, _exists)

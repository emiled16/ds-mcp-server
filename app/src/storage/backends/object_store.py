import asyncio
import io
from concurrent.futures import ThreadPoolExecutor

from minio import Minio
from minio.error import S3Error

from src.storage.interfaces import ObjectStore


class MinIOObjectStore(ObjectStore):
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = False,
    ):
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region="us-east-1",  # Required for MinIO, even if not used
        )
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def put(self, bucket: str, key: str, data: bytes) -> str:
        loop = asyncio.get_event_loop()

        bucket_exists = await loop.run_in_executor(self._executor, self.client.bucket_exists, bucket)
        if not bucket_exists:
            await loop.run_in_executor(self._executor, self.client.make_bucket, bucket)

        data_stream = io.BytesIO(data)

        def _put():
            self.client.put_object(
                bucket_name=bucket,
                object_name=key,
                data=data_stream,
                length=len(data),
            )

        await loop.run_in_executor(self._executor, _put)

        return key

    async def get(self, bucket: str, key: str) -> bytes | None:
        loop = asyncio.get_event_loop()

        def _get():
            try:
                response = self.client.get_object(bucket, key)
                return response.read()
            except S3Error as e:
                if e.code == "NoSuchKey":
                    return None
                raise

        return await loop.run_in_executor(self._executor, _get)

    async def delete(self, bucket: str, key: str) -> bool:
        loop = asyncio.get_event_loop()

        def _delete() -> bool:
            try:
                self.client.remove_object(bucket, key)
                return True
            except S3Error:
                return False

        return await loop.run_in_executor(self._executor, _delete)

    async def exists(self, bucket: str, key: str) -> bool:
        loop = asyncio.get_event_loop()

        def _exists() -> bool:
            try:
                self.client.stat_object(bucket, key)
                return True
            except S3Error:
                return False

        return await loop.run_in_executor(self._executor, _exists)

import io
import pickle
import sys
from typing import Any

import polars as pl

from src.models.tool_response import ToolResponse
from src.storage.interfaces import BaseRepository, DocumentStore, ObjectStore


class ObjectStoreError(Exception):
    """Raised when object store operations fail."""


class PayloadNotFoundError(Exception):
    """Raised when payload cannot be found in object store."""


class ToolResponseRepository(BaseRepository[ToolResponse]):
    def __init__(
        self,
        document_store: DocumentStore,
        object_store: ObjectStore | None = None,
        cache: dict[str, Any] | None = None,
        cache_size_limit: int = 10 * 1024 * 1024,  # 10MB
        object_store_threshold: int = 1024 * 1024,  # 1MB
    ) -> None:
        self.doc_store = document_store
        self.obj_store = object_store
        self.cache = cache if cache is not None else {}
        self.cache_size_limit = cache_size_limit
        self.object_store_threshold = object_store_threshold
        self.collection = "tool_responses"
        self.bucket = "tool-responses"  # S3 bucket names cannot contain underscores
        self.current_version = 1

    async def save(self, tool_response: ToolResponse) -> ToolResponse:
        data = tool_response.model_dump()
        # Document store will convert entity_id to _id automatically

        payload_ref = None
        storage_metadata = {}
        payload = tool_response.payload

        # Check if payload needs object storage
        if self._needs_object_storage(payload):
            if not self.obj_store:
                raise ObjectStoreError("Object store required for large payloads but not provided")

            key = f"{tool_response.entity_id}/payload"

            if isinstance(payload, pl.DataFrame):
                buffer = io.BytesIO()
                payload.write_parquet(buffer)
                serialized = buffer.getvalue()
                storage_metadata = {"format": "parquet", "type": "polars.DataFrame"}
            else:
                serialized = pickle.dumps(payload)
                storage_metadata = {"format": "pickle", "type": type(payload).__name__}

            await self.obj_store.put(self.bucket, key, serialized)

            payload_ref = {
                "type": "object_store",
                "bucket": self.bucket,
                "key": key,
                **storage_metadata,
            }
            data["payload_ref"] = payload_ref
            data.pop("payload", None)
        else:
            data["payload"] = self._serialize_for_storage(payload)

        await self.doc_store.create(self.collection, data)

        if not payload_ref and self._get_size(payload) < self.cache_size_limit:
            self.cache[tool_response.entity_id] = payload

        return tool_response

    async def get(self, entity_id: str) -> ToolResponse | None:
        doc = await self.doc_store.read(self.collection, entity_id)
        if not doc:
            return None

        # Document store automatically converts _id to both id and entity_id
        payload_ref = doc.pop("payload_ref", None)

        if entity_id in self.cache:
            doc["payload"] = self.cache[entity_id]
            return ToolResponse.model_validate(doc)

        if payload_ref:
            payload = await self._load_payload_from_ref(payload_ref, entity_id)
            doc["payload"] = payload

        return ToolResponse.model_validate(doc)

    # async def load_payload(self, tool_response: ToolResponse) -> ToolResponse:
    #     if tool_response.payload is not None:
    #         return tool_response

    #     payload_ref = getattr(tool_response, "payload_ref", None)
    #     if not payload_ref:
    #         return tool_response

    #     if not isinstance(payload_ref, dict):
    #         raise ValueError(f"Invalid payload_ref type: {type(payload_ref)}")

    #     tool_response.payload = await self._load_payload_from_ref(payload_ref, tool_response.entity_id)

    #     if hasattr(tool_response, "payload_ref"):
    #         delattr(tool_response, "payload_ref")

    #     return tool_response

    async def delete(self, entity_id: str) -> bool:
        doc = await self.doc_store.read(self.collection, entity_id)
        if not doc:
            return False

        if "payload_ref" in doc and self.obj_store:
            ref = doc["payload_ref"]
            if isinstance(ref, dict) and "bucket" in ref and "key" in ref:
                await self.obj_store.delete(ref["bucket"], ref["key"])

        self.cache.pop(entity_id, None)

        return await self.doc_store.delete(self.collection, entity_id)

    async def list(self, filters: dict | None = None) -> list[ToolResponse]:
        query = filters or {}
        docs = await self.doc_store.find(self.collection, query)

        tool_responses = []
        for doc in docs:
            # Document store automatically converts _id to both id and entity_id
            # Extract payload_ref before validation
            payload_ref = doc.pop("payload_ref", None)

            # Set payload to None if it was stored in object store
            if payload_ref:
                doc["payload"] = None

            tool_response = ToolResponse.model_validate(doc)
            tool_responses.append(tool_response)

        return tool_responses

    async def get_entity_type(self) -> str:
        return "tool_response"

    def _needs_object_storage(self, value: Any) -> bool:
        if isinstance(value, pl.DataFrame):
            return True
        size = self._get_size(value)
        return size > self.object_store_threshold

    def _get_size(self, value: Any) -> int:
        if isinstance(value, pl.DataFrame):
            try:
                return value.estimated_size()
            except AttributeError:
                # Fallback: rough estimate assuming average 8 bytes per cell
                # This is conservative - actual size varies by data types
                # Since all DataFrames go to object storage anyway, this is only
                # used for cache size decisions, so being conservative is fine
                return value.height * value.width * 8
        try:
            return sys.getsizeof(value)
        except (TypeError, AttributeError):
            return 0

    def _serialize_for_storage(self, value: Any) -> Any:
        return value

    async def _load_payload_from_ref(self, payload_ref: dict[str, Any], entity_id: str) -> Any:
        if not self.obj_store:
            raise ObjectStoreError("Object store required but not provided")

        if not isinstance(payload_ref, dict) or "bucket" not in payload_ref or "key" not in payload_ref:
            raise ValueError(f"Invalid payload_ref format: {payload_ref}")

        data = await self.obj_store.get(payload_ref["bucket"], payload_ref["key"])

        if data is None:
            raise PayloadNotFoundError(f"Payload not found in object store: {payload_ref['key']}")

        format_type = payload_ref.get("format")
        if format_type == "parquet" and payload_ref.get("type") == "polars.DataFrame":
            buffer = io.BytesIO(data)
            value = pl.read_parquet(buffer)
        else:
            try:
                # Note: pickle is used here for trusted data stored by this system
                value = pickle.loads(data)  # noqa: S301
            except (pickle.UnpicklingError, EOFError, AttributeError, ImportError) as e:
                raise ValueError(f"Failed to deserialize payload: {e}") from e

        # Cache if small enough
        if self._get_size(value) < self.cache_size_limit:
            self.cache[entity_id] = value

        return value

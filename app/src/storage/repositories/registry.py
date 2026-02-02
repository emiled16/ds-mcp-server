from __future__ import annotations

from typing import Any

from src.storage.entities import detect_entity_type
from src.storage.interfaces import BaseRepository, DocumentStore, ObjectStore
from src.storage.repositories.job import JobRepository
from src.storage.repositories.note import NoteRepository
from src.storage.repositories.tool_response import ToolResponseRepository
from src.types.messages import EntityType

# Module-level registry instance (singleton pattern)
_registry: RepositoryRegistry | None = None  # type: ignore[name-defined]


class RepositoryRegistry:
    def __init__(
        self,
        document_store: DocumentStore,
        object_store: ObjectStore | None = None,
    ) -> None:
        self.doc_store = document_store
        self.obj_store = object_store
        self._repositories: dict[str, BaseRepository[Any]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return

        self._repositories["tool_response"] = ToolResponseRepository(
            document_store=self.doc_store,
            object_store=self.obj_store,
        )

        self._repositories["job"] = JobRepository(
            document_store=self.doc_store,
        )

        self._repositories["note"] = NoteRepository(
            document_store=self.doc_store,
        )

        self._initialized = True
        set_repository_registry(self)

    def get_repository(self, entity_type: str) -> BaseRepository[Any]:
        if not self._initialized:
            raise RuntimeError("Registry not initialized. Call initialize() first.")

        repo = self._repositories.get(entity_type)
        if not repo:
            raise ValueError(f"No repository registered for entity type: {entity_type}")

        return repo

    async def save(self, entity: Any) -> Any:
        entity_type = detect_entity_type(entity)
        repo = self.get_repository(entity_type)
        return await repo.save(entity)

    async def get(self, entity_type: EntityType, entity_id: str) -> Any:
        repo = self.get_repository(entity_type)
        return await repo.get(entity_id)

    async def delete(self, entity_type: EntityType, entity_id: str) -> bool:
        repo = self.get_repository(entity_type)
        return await repo.delete(entity_id)

    async def list(self, entity_type: EntityType, filters: dict | None = None) -> list[Any]:
        repo = self.get_repository(entity_type)
        return await repo.list(filters)

    def list_entity_types(self) -> list[EntityType]:
        return list(self._repositories.keys())


def get_repository_registry() -> RepositoryRegistry:
    if _registry is None:
        raise RuntimeError("RepositoryRegistry not initialized. Call initialize() first.")
    return _registry


def set_repository_registry(registry: RepositoryRegistry) -> None:
    global _registry  # noqa: PLW0603
    _registry = registry

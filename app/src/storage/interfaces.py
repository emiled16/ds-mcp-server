from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class DocumentStore(ABC):
    @abstractmethod
    async def create(self, collection: str, document: dict) -> str: ...

    @abstractmethod
    async def read(self, collection: str, entity_id: str) -> dict | None: ...

    @abstractmethod
    async def update(self, collection: str, entity_id: str, document: dict) -> bool: ...

    @abstractmethod
    async def delete(self, collection: str, entity_id: str) -> bool: ...

    @abstractmethod
    async def find(self, collection: str, query: dict) -> list[dict]: ...


class ObjectStore(ABC):
    @abstractmethod
    async def put(self, bucket: str, key: str, data: bytes) -> str: ...

    @abstractmethod
    async def get(self, bucket: str, key: str) -> bytes | None: ...

    @abstractmethod
    async def delete(self, bucket: str, key: str) -> bool: ...

    @abstractmethod
    async def exists(self, bucket: str, key: str) -> bool: ...


class BaseRepository(ABC, Generic[T]):
    @abstractmethod
    async def save(self, entity: T) -> T: ...

    @abstractmethod
    async def get(self, entity_id: str) -> T | None: ...

    @abstractmethod
    async def delete(self, entity_id: str) -> bool: ...

    @abstractmethod
    async def list(self, filters: dict | None = None) -> list[T]: ...

    @abstractmethod
    async def get_entity_type(self) -> str: ...

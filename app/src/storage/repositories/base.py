from typing import Generic, TypeVar

from src.storage.interfaces import BaseRepository

T = TypeVar("T")


class Repository(BaseRepository[T], Generic[T]):
    def __init__(self, collection_name: str) -> None:
        self.collection_name = collection_name

    async def get_entity_type(self) -> str:
        return self.collection_name

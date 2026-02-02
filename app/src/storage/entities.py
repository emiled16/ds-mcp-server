from typing import Protocol

from src.types.messages import EntityType


class Entity(Protocol):
    entity_id: str
    type: EntityType
    version: int = 1


def detect_entity_type(entity: Entity) -> str:
    return getattr(entity, "type", None)

"""Note repository for persisting notes."""

from __future__ import annotations

from datetime import datetime

from src.models.note import Note
from src.storage.interfaces import DocumentStore
from src.storage.repositories.base import BaseRepository


class NoteRepository(BaseRepository[Note]):
    """Repository for Note entities.

    Stores notes in the document store (Postgres) for persistence across sessions.
    """

    def __init__(self, document_store: DocumentStore) -> None:
        """Initialize the repository.

        Args:
            document_store: Document store for persistence (e.g. Postgres)
        """
        self.doc_store = document_store
        self.collection = "notes"

    async def get_entity_type(self) -> str:
        """Get the entity type this repository handles."""
        return "note"

    async def save(self, note: Note) -> Note:
        """Save a note to the database.

        Args:
            note: Note to save

        Returns:
            Saved note with updated timestamp
        """
        note.updated_at = datetime.utcnow()

        # Check if note exists
        existing = await self.doc_store.read(self.collection, note.entity_id)

        if existing:
            await self.doc_store.update(self.collection, note.entity_id, note.to_dict())
        else:
            await self.doc_store.create(self.collection, note.to_dict())

        return note

    async def get(self, entity_id: str) -> Note | None:
        """Get a note by entity_id.

        Args:
            entity_id: Note entity ID

        Returns:
            Note if found, None otherwise
        """
        doc = await self.doc_store.read(self.collection, entity_id)
        return Note.from_dict(doc) if doc else None

    async def get_by_title(self, title: str) -> Note | None:
        """Get a note by title (case-insensitive).

        Args:
            title: Note title

        Returns:
            Note if found, None otherwise
        """
        docs = await self.doc_store.find(
            self.collection,
            {"title": {"$regex": f"^{title}$", "$options": "i"}},
        )
        return Note.from_dict(docs[0]) if docs else None

    async def list(self, filters: dict | None = None) -> list[Note]:
        """List notes with optional filters.

        Args:
            filters: Optional filter criteria

        Returns:
            List of matching notes
        """
        docs = await self.doc_store.find(self.collection, filters or {})
        notes = [Note.from_dict(doc) for doc in docs]
        # Sort by updated_at descending
        notes.sort(key=lambda n: n.updated_at, reverse=True)
        return notes

    async def search(self, query: str, limit: int = 10) -> list[Note]:
        """Search notes by title or content.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching notes
        """
        # Simple text search (could be enhanced with full-text index)
        docs = await self.doc_store.find(
            self.collection,
            {
                "$or": [
                    {"title": {"$regex": query, "$options": "i"}},
                    {"content": {"$regex": query, "$options": "i"}},
                    {"tags": {"$in": [query]}},
                ],
            },
        )
        notes = [Note.from_dict(doc) for doc in docs]
        notes.sort(key=lambda n: n.updated_at, reverse=True)
        return notes[:limit]

    async def list_by_tag(self, tag: str) -> list[Note]:
        """List notes with a specific tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of matching notes
        """
        docs = await self.doc_store.find(
            self.collection,
            {"tags": tag},
        )
        notes = [Note.from_dict(doc) for doc in docs]
        notes.sort(key=lambda n: n.updated_at, reverse=True)
        return notes

    async def list_by_reference(self, entity_id: str) -> list[Note]:
        """List notes that reference a specific entity.

        Args:
            entity_id: Entity ID to search for in references

        Returns:
            List of notes referencing the entity
        """
        docs = await self.doc_store.find(
            self.collection,
            {"references": entity_id},
        )
        return [Note.from_dict(doc) for doc in docs]

    async def delete(self, entity_id: str) -> bool:
        """Delete a note.

        Args:
            entity_id: Note entity ID

        Returns:
            True if deleted, False if not found
        """
        return await self.doc_store.delete(self.collection, entity_id)

    async def get_all_tags(self) -> list[str]:
        """Get all unique tags across notes.

        Returns:
            List of unique tags
        """
        docs = await self.doc_store.find(self.collection, {})
        all_tags = set()
        for doc in docs:
            all_tags.update(doc.get("tags", []))
        return sorted(all_tags)

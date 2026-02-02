"""Note model for tracking findings, analysis, and documentation.

Notes allow the agent to persist information across conversations
and build up documentation of the data science workflow.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class Note(BaseModel):
    """Note entity for persisting agent findings and documentation.

    Notes are markdown documents that can be created, updated, and
    referenced throughout the data science workflow.
    """

    entity_id: str = Field(
        default_factory=lambda: f"note_{uuid.uuid4().hex[:12]}",
        description="Unique note identifier",
    )
    type: str = Field(default="note", description="Entity type for storage")
    version: int = Field(default=1, description="Schema version")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the note was created",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the note was last updated",
    )

    # Content
    title: str = Field(..., description="Note title")
    content: str = Field(default="", description="Note content (markdown)")

    # Organization
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    references: list[str] = Field(
        default_factory=list,
        description="Entity IDs of related tool responses",
    )

    # Metadata
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    model_config = {"arbitrary_types_allowed": True}

    def append(self, content: str, separator: str = "\n\n") -> "Note":
        """Append content to the note."""
        self.content = self.content + separator + content if self.content else content
        self.updated_at = datetime.utcnow()
        return self

    def add_reference(self, entity_id: str) -> "Note":
        """Add a reference to another entity."""
        if entity_id not in self.references:
            self.references.append(entity_id)
            self.updated_at = datetime.utcnow()
        return self

    def add_tag(self, tag: str) -> "Note":
        """Add a tag to the note."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.utcnow()
        return self

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "entity_id": self.entity_id,
            "type": self.type,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "references": self.references,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Note":
        """Create from dictionary."""
        data = data.copy()

        # Parse timestamps
        for field in ["created_at", "updated_at"]:
            if data.get(field) and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])

        return cls(**data)

    @property
    def word_count(self) -> int:
        """Get word count of content."""
        return len(self.content.split()) if self.content else 0

    @property
    def preview(self) -> str:
        """Get a preview of the content (first 200 chars)."""
        if len(self.content) <= 200:
            return self.content
        return self.content[:200] + "..."

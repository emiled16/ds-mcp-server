"""Create note tool."""

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.note import Note
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def create_note(
    title: str,
    content: str = "",
    tags: list[str] | None = None,
    references: list[str] | None = None,
) -> str:
    """Create a new note to document findings, analysis, or plans.

    Notes are persistent markdown documents that can be used to track
    the data science workflow, document findings, and build reports.

    Args:
        title: Title of the note (should be descriptive)
        content: Initial content (markdown supported)
        tags: Optional list of tags for categorization
        references: Optional list of entity_ids to reference

    Returns:
        ToolResponse with the created note

    Example:
        "Create a note about the sales analysis"
        → create_note(
            title="Sales Data Analysis",
            content="## Overview\\nInitial analysis of Q4 sales data...",
            tags=["analysis", "sales"]
        )
    """
    try:
        # Create note
        note = Note(
            title=title,
            content=content,
            tags=tags or [],
            references=references or [],
        )

        # Save to repository
        registry = get_repository_registry()
        note_repo = registry.get_repository("note")
        saved_note = await note_repo.save(note)

        summary = f"Created note: '{saved_note.title}'\n\n"
        summary += f"Note ID: {saved_note.entity_id}\n"
        summary += f"Word count: {saved_note.word_count}\n"
        if saved_note.tags:
            summary += f"Tags: {', '.join(saved_note.tags)}\n"
        if saved_note.references:
            summary += f"References: {len(saved_note.references)} entity(s)\n"

        summary += "\nUse update_note() or append_to_note() to add more content."

        return ToolResponse(
            payload={
                "note_id": saved_note.entity_id,
                "title": saved_note.title,
                "content": saved_note.content,
                "tags": saved_note.tags,
                "references": saved_note.references,
            },
            summary=summary,
            metadata={"note_id": saved_note.entity_id},
            storage_hint="always",
            suggested_name=f"note_{title.lower().replace(' ', '_')[:20]}",
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error creating note: {e}",
            metadata={"error": type(e).__name__},
            storage_hint="never",
        )

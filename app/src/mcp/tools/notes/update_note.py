"""Update note tool."""

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def update_note(
    note_id: str,
    content: str | None = None,
    title: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Update an existing note's content, title, or tags.

    Replaces the specified fields with new values. Fields not specified
    are left unchanged.

    Args:
        note_id: ID of the note to update
        content: New content (replaces existing content)
        title: New title
        tags: New tags (replaces existing tags)

    Returns:
        ToolResponse with the updated note

    Example:
        "Update note_abc123 with new analysis results"
        → update_note(
            note_id="note_abc123",
            content="## Updated Analysis\\nAfter further investigation..."
        )

        "Change the title and tags"
        → update_note(
            note_id="note_abc123",
            title="Final Sales Analysis",
            tags=["analysis", "sales", "final"]
        )
    """
    try:
        registry = get_repository_registry()
        note_repo = registry.get_repository("note")

        # Get existing note
        note = await note_repo.get(note_id)

        if not note:
            return ToolResponse(
                payload=None,
                summary=f"Error: Note '{note_id}' not found.",
                metadata={"error": "NotFound", "note_id": note_id},
                storage_hint="never",
            )

        # Update fields
        if content is not None:
            note.content = content
        if title is not None:
            note.title = title
        if tags is not None:
            note.tags = tags

        # Save updated note
        saved_note = await note_repo.save(note)

        summary = f"Updated note: '{saved_note.title}'\n\n"
        summary += f"Note ID: {saved_note.entity_id}\n"
        summary += f"Word count: {saved_note.word_count}\n"
        summary += f"Last updated: {saved_note.updated_at.strftime('%Y-%m-%d %H:%M')}\n"
        if saved_note.tags:
            summary += f"Tags: {', '.join(saved_note.tags)}\n"

        return ToolResponse(
            payload={
                "note_id": saved_note.entity_id,
                "title": saved_note.title,
                "content": saved_note.content,
                "tags": saved_note.tags,
                "word_count": saved_note.word_count,
            },
            summary=summary,
            metadata={"note_id": note_id},
            storage_hint="always",
            suggested_name=f"note_{saved_note.title.lower().replace(' ', '_')[:20]}",
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error updating note: {e}",
            metadata={"error": type(e).__name__, "note_id": note_id},
            storage_hint="never",
        )

"""Get note tool."""

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def get_note(note_id: str, full_content: bool = True) -> str:
    """Retrieve a note by its ID.

    Gets the full content and metadata of a note.

    Args:
        note_id: ID of the note to retrieve
        full_content: If True, return full content; if False, return preview only

    Returns:
        ToolResponse with the note content

    Example:
        "Get note_abc123"
        → get_note(note_id="note_abc123")

        "Get preview of note_abc123"
        → get_note(note_id="note_abc123", full_content=False)
    """
    try:
        registry = get_repository_registry()
        note_repo = registry.get_repository("note")

        # Get note
        note = await note_repo.get(note_id)

        if not note:
            return ToolResponse(
                payload=None,
                summary=f"Error: Note '{note_id}' not found.",
                metadata={"error": "NotFound", "note_id": note_id},
                storage_hint="never",
            )

        # Build summary
        summary = f"# {note.title}\n\n"
        summary += f"Note ID: {note.entity_id}\n"
        summary += f"Created: {note.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        summary += f"Updated: {note.updated_at.strftime('%Y-%m-%d %H:%M')}\n"
        summary += f"Word count: {note.word_count}\n"

        if note.tags:
            summary += f"Tags: {', '.join(note.tags)}\n"
        if note.references:
            summary += f"References: {len(note.references)} entity(s)\n"

        summary += "\n---\n\n"

        if full_content:
            summary += note.content
        else:
            summary += note.preview
            if len(note.content) > 200:
                summary += f"\n\n[...truncated, {note.word_count} total words]"

        return ToolResponse(
            payload={
                "note_id": note.entity_id,
                "title": note.title,
                "content": note.content if full_content else note.preview,
                "tags": note.tags,
                "references": note.references,
                "word_count": note.word_count,
                "created_at": note.created_at.isoformat(),
                "updated_at": note.updated_at.isoformat(),
            },
            summary=summary,
            metadata={"note_id": note_id, "full_content": full_content},
            storage_hint="never",
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error getting note: {e}",
            metadata={"error": type(e).__name__, "note_id": note_id},
            storage_hint="never",
        )

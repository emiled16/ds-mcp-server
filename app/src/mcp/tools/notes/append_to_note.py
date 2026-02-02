"""Append to note tool."""

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def append_to_note(
    note_id: str,
    content: str,
    add_timestamp: bool = False,
    add_reference: str | None = None,
) -> str:
    """Append content to an existing note.

    Adds new content to the end of the note without replacing existing content.
    Useful for building up documentation incrementally.

    Args:
        note_id: ID of the note to append to
        content: Content to append (markdown supported)
        add_timestamp: If True, add a timestamp header before the content
        add_reference: Optional entity_id to add as a reference

    Returns:
        ToolResponse with the updated note

    Example:
        "Add findings to note_abc123"
        → append_to_note(
            note_id="note_abc123",
            content="### New Findings\\n- Feature X has 85% correlation with target"
        )

        "Add timestamped entry"
        → append_to_note(
            note_id="note_abc123",
            content="Completed data profiling phase",
            add_timestamp=True
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

        # Build content to append
        append_content = ""
        if add_timestamp:
            from datetime import datetime

            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            append_content = f"---\n*{timestamp}*\n\n"

        append_content += content

        # Append to note
        note.append(append_content)

        # Add reference if provided
        if add_reference:
            note.add_reference(add_reference)

        # Save updated note
        saved_note = await note_repo.save(note)

        summary = f"Appended to note: '{saved_note.title}'\n\n"
        summary += f"Note ID: {saved_note.entity_id}\n"
        summary += f"Total word count: {saved_note.word_count}\n"
        summary += f"Last updated: {saved_note.updated_at.strftime('%Y-%m-%d %H:%M')}\n"
        if add_reference:
            summary += f"Added reference: {add_reference}\n"

        # Show last part of content
        lines = saved_note.content.split("\n")
        last_lines = "\n".join(lines[-10:])
        summary += f"\nLast 10 lines:\n{last_lines}"

        return ToolResponse(
            payload={
                "note_id": saved_note.entity_id,
                "title": saved_note.title,
                "word_count": saved_note.word_count,
                "references": saved_note.references,
            },
            summary=summary,
            metadata={"note_id": note_id, "added_reference": add_reference},
            storage_hint="always",
            suggested_name=f"note_{saved_note.title.lower().replace(' ', '_')[:20]}",
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error appending to note: {e}",
            metadata={"error": type(e).__name__, "note_id": note_id},
            storage_hint="never",
        )

"""List notes tool."""

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def list_notes(tag: str | None = None, limit: int = 20) -> str:
    """List all notes, optionally filtered by tag.

    Shows a summary of all notes with their titles and metadata.

    Args:
        tag: Optional tag to filter by
        limit: Maximum number of notes to return (default: 20)

    Returns:
        ToolResponse with list of notes

    Example:
        "List all notes"
        → list_notes()

        "List notes tagged 'analysis'"
        → list_notes(tag="analysis")
    """
    try:
        registry = get_repository_registry()
        note_repo = registry.get_repository("note")

        # Get notes
        if tag:
            notes = await note_repo.list_by_tag(tag)
        else:
            notes = await note_repo.list()

        # Limit results
        notes = notes[:limit]

        if not notes:
            summary = "No notes found"
            if tag:
                summary += f" with tag '{tag}'"
            summary += ".\n\nCreate a note with create_note() to get started."

            return ToolResponse(
                payload=[],
                summary=summary,
                metadata={"count": 0, "tag_filter": tag},
                storage_hint="never",
            )

        # Get all tags for summary
        all_tags = await note_repo.get_all_tags()

        # Build summary
        summary = f"Notes ({len(notes)}"
        if tag:
            summary += f", filtered by tag: '{tag}'"
        summary += "):\n\n"

        summary += f"{'ID':<20} {'Title':<30} {'Updated':<12} {'Words':>8}\n"
        summary += "-" * 75 + "\n"

        for note in notes:
            title = note.title[:27] + "..." if len(note.title) > 30 else note.title
            updated = note.updated_at.strftime("%Y-%m-%d")
            summary += f"{note.entity_id:<20} {title:<30} {updated:<12} {note.word_count:>8}\n"

        if all_tags:
            summary += f"\nAvailable tags: {', '.join(all_tags[:10])}"
            if len(all_tags) > 10:
                summary += f" ... and {len(all_tags) - 10} more"

        summary += "\n\nUse get_note(note_id='...') to view a note's full content."

        # Convert to serializable format
        notes_data = [
            {
                "note_id": n.entity_id,
                "title": n.title,
                "tags": n.tags,
                "word_count": n.word_count,
                "updated_at": n.updated_at.isoformat(),
            }
            for n in notes
        ]

        return ToolResponse(
            payload=notes_data,
            summary=summary,
            metadata={
                "count": len(notes),
                "tag_filter": tag,
                "all_tags": all_tags,
            },
            storage_hint="never",
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error listing notes: {e}",
            metadata={"error": type(e).__name__},
            storage_hint="never",
        )

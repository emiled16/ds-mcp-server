"""Search notes tool."""

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def search_notes(query: str, limit: int = 10) -> str:
    """Search notes by title, content, or tags.

    Searches across all notes for matching text.

    Args:
        query: Search query (searches title, content, and tags)
        limit: Maximum number of results (default: 10)

    Returns:
        ToolResponse with matching notes

    Example:
        "Search notes for 'feature engineering'"
        → search_notes(query="feature engineering")

        "Find notes tagged with 'analysis'"
        → search_notes(query="analysis")
    """
    try:
        registry = get_repository_registry()
        note_repo = registry.get_repository("note")

        # Search notes
        notes = await note_repo.search(query, limit=limit)

        if not notes:
            return ToolResponse(
                payload=[],
                summary=f"No notes found matching '{query}'.",
                metadata={"query": query, "count": 0},
                storage_hint="never",
            )

        # Build summary
        summary = f"Found {len(notes)} note(s) matching '{query}':\n\n"

        for note in notes:
            summary += f"• **{note.title}** ({note.entity_id})\n"
            summary += f"  Updated: {note.updated_at.strftime('%Y-%m-%d %H:%M')}"
            summary += f" | Words: {note.word_count}"
            if note.tags:
                summary += f" | Tags: {', '.join(note.tags[:3])}"
            summary += "\n"
            # Show preview
            preview = note.preview[:100] + "..." if len(note.preview) > 100 else note.preview
            summary += f"  > {preview}\n\n"

        summary += "\nUse get_note(note_id='...') to view full content."

        # Convert to serializable format
        notes_data = [
            {
                "note_id": n.entity_id,
                "title": n.title,
                "preview": n.preview,
                "tags": n.tags,
                "word_count": n.word_count,
                "updated_at": n.updated_at.isoformat(),
            }
            for n in notes
        ]

        return ToolResponse(
            payload=notes_data,
            summary=summary,
            metadata={"query": query, "count": len(notes)},
            storage_hint="never",
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error searching notes: {e}",
            metadata={"error": type(e).__name__, "query": query},
            storage_hint="never",
        )

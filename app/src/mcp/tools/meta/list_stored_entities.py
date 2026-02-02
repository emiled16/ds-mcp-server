"""List stored entities tool."""

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse


@mcp.tool
@process_tool
@register_tool
async def list_stored_entities(
    entity_type: str | None = None,
    limit: int = 50,
) -> str:
    """List all stored entities (datasets, jobs, notes) in the current session.

    Shows entity_ids with their metadata so you can reference them in subsequent operations.
    This is your "memory" of what data and results are available.

    Args:
        entity_type: Optional filter by type ('tool_response', 'job', 'note')
        limit: Maximum number of entities to return (default: 50)

    Returns:
        Summary of stored entities with their entity_ids

    Example:
        "What datasets do I have loaded?"
        → list_stored_entities(entity_type="tool_response")

        "Show me all my notes"
        → list_stored_entities(entity_type="note")

        "What's in my session?"
        → list_stored_entities()
    """
    from src.storage.repositories.registry import get_repository_registry

    registry = get_repository_registry()

    entities_by_type: dict[str, list[dict]] = {
        "tool_response": [],
        "job": [],
        "note": [],
    }

    # Filter by type if specified
    types_to_check = [entity_type] if entity_type else list(entities_by_type.keys())

    for etype in types_to_check:
        if etype not in entities_by_type:
            continue

        try:
            repo = registry._repositories.get(etype)
            if repo:
                # Get entities from repository
                if hasattr(repo, "list"):
                    items = await repo.list()
                    for item in items[:limit]:
                        if etype == "tool_response":
                            entities_by_type[etype].append(
                                {
                                    "entity_id": item.entity_id,
                                    "suggested_name": item.suggested_name,
                                    "storage_hint": item.storage_hint,
                                    "has_payload": item.payload is not None,
                                    "metadata_keys": list(item.metadata.keys()) if item.metadata else [],
                                }
                            )
                        elif etype == "job":
                            entities_by_type[etype].append(
                                {
                                    "entity_id": item.entity_id,
                                    "task_name": item.task_name,
                                    "status": item.status.value if hasattr(item.status, "value") else item.status,
                                    "created_at": str(item.created_at) if item.created_at else None,
                                }
                            )
                        elif etype == "note":
                            entities_by_type[etype].append(
                                {
                                    "entity_id": item.entity_id,
                                    "title": item.title,
                                    "tags": item.tags,
                                    "word_count": item.word_count,
                                }
                            )
        except Exception:
            # Repository might not be initialized or have list method
            pass

    # Build summary
    total = sum(len(items) for items in entities_by_type.values())

    if total == 0:
        return ToolResponse(
            payload=entities_by_type,
            summary="No stored entities found in this session.\n\n"
            "Load data with `load_csv()` or `load_excel()` to get started.",
            metadata={"total": 0},
            storage_hint="never",
        )

    summary = "# Stored Entities\n\n"

    # Datasets (tool_responses)
    datasets = entities_by_type.get("tool_response", [])
    if datasets:
        summary += f"## 📊 Datasets ({len(datasets)})\n\n"
        summary += "| entity_id | name | has_data |\n"
        summary += "|-----------|------|----------|\n"
        for ds in datasets[:20]:
            name = ds.get("suggested_name") or "unnamed"
            has_data = "✅" if ds.get("has_payload") else "❌"
            summary += f"| `{ds['entity_id'][:20]}...` | {name} | {has_data} |\n"
        if len(datasets) > 20:
            summary += f"\n... and {len(datasets) - 20} more\n"
        summary += "\n"

    # Jobs
    jobs = entities_by_type.get("job", [])
    if jobs:
        summary += f"## ⚙️ Jobs ({len(jobs)})\n\n"
        summary += "| entity_id | task | status |\n"
        summary += "|-----------|------|--------|\n"
        for job in jobs[:20]:
            status_emoji = {
                "PENDING": "⏳",
                "RUNNING": "🔄",
                "SUCCESS": "✅",
                "FAILURE": "❌",
                "REVOKED": "🚫",
            }.get(job.get("status", ""), "❓")
            summary += (
                f"| `{job['entity_id']}` | {job.get('task_name', 'unknown')} | {status_emoji} {job.get('status')} |\n"
            )
        summary += "\n"

    # Notes
    notes = entities_by_type.get("note", [])
    if notes:
        summary += f"## 📝 Notes ({len(notes)})\n\n"
        summary += "| entity_id | title | tags |\n"
        summary += "|-----------|-------|------|\n"
        for note in notes[:20]:
            tags = ", ".join(note.get("tags", [])[:3])
            if len(note.get("tags", [])) > 3:
                tags += "..."
            summary += f"| `{note['entity_id'][:20]}...` | {note.get('title', 'Untitled')[:30]} | {tags} |\n"
        summary += "\n"

    summary += f"\n**Total entities**: {total}\n"
    summary += "\nUse these `entity_id` values to reference data in other tools."

    return ToolResponse(
        payload=entities_by_type,
        summary=summary,
        metadata={"total": total, "by_type": {k: len(v) for k, v in entities_by_type.items()}},
        storage_hint="never",
    )

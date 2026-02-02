"""Load dataset by entity_id tool."""

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def load_dataset(entity_id: str) -> str:
    """Load a previously stored dataset by entity_id.

    Retrieves a dataset that was loaded in a previous tool call using its entity_id.
    This is useful for referencing data across multiple tool calls without re-loading.

    Args:
        entity_id: Entity ID of the stored dataset (e.g., 'abc123-def456...')

    Returns:
        ToolResponse with the dataset and updated summary

    Example:
        "Load the dataset abc123-def456"
        → load_dataset(entity_id="abc123-def456")
    """
    try:
        registry = get_repository_registry()
        entity = await registry.get("tool_response", entity_id)

        if not entity:
            return ToolResponse(
                payload=None,
                summary=f"Error: Dataset with entity_id '{entity_id}' not found.\n"
                "The dataset may have expired or was not stored.\n"
                "Use list_available_datasets() to see available files, "
                "or load a new file with load_csv().",
                metadata={"error": "NotFound", "entity_id": entity_id},
                storage_hint="never",
            )

        payload = entity.payload

        # Check if payload is a DataFrame
        if hasattr(payload, "shape"):
            rows, cols = payload.shape
            summary = (
                f"Loaded dataset '{entity_id}':\n"
                f"  • Rows: {rows:,}\n"
                f"  • Columns: {cols}\n"
                f"  • Original name: {entity.suggested_name or 'unknown'}\n"
            )

            # Add preview if it's a DataFrame
            if hasattr(payload, "head"):
                preview = payload.head(3).to_string(max_cols=10, max_colwidth=30)
                summary += f"\nPreview (first 3 rows):\n{preview}"
        else:
            summary = (
                f"Loaded entity '{entity_id}':\n"
                f"  • Type: {type(payload).__name__}\n"
                f"  • Original summary: {entity.summary[:200]}..."
            )

        return ToolResponse(
            payload=payload,
            summary=summary,
            metadata={
                "entity_id": entity_id,
                "original_metadata": entity.metadata,
                "suggested_name": entity.suggested_name,
            },
            storage_hint="session",
            suggested_name=entity.suggested_name,
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error loading dataset: {e}",
            metadata={"error": type(e).__name__, "entity_id": entity_id},
            storage_hint="never",
        )

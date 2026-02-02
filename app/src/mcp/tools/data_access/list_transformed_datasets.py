"""List transformed datasets with metadata."""

from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def list_transformed_datasets(
    source_dataset_id: str | None = None,
    pipeline_name: str | None = None,
    limit: int = 50,
) -> str:
    """List transformed datasets with their metadata.

    Browse transformed datasets created by feature pipelines, with optional
    filtering by source dataset or pipeline name.

    Args:
        source_dataset_id: Optional filter by source dataset entity ID
        pipeline_name: Optional filter by pipeline name
        limit: Maximum number of datasets to return (default: 50)

    Returns:
        ToolResponse with list of transformed datasets and metadata

    Example:
        "List all transformed datasets"
        → list_transformed_datasets()

        "Show datasets transformed from the sales data"
        → list_transformed_datasets(source_dataset_id="sales_data_123")

        "Find datasets created by the feature_pipeline"
        → list_transformed_datasets(pipeline_name="customer_features")
    """
    try:
        registry = get_repository_registry()

        # Get all tool responses
        repo = registry.get_repository("tool_response")
        all_entities = await repo.list()

        # Filter for transformed datasets
        transformed_datasets = []

        for entity in all_entities:
            metadata = entity.get("metadata", {})

            # Check if this is a transformed dataset
            is_transformed = metadata.get("is_transformed_dataset", False)
            if not is_transformed:
                continue

            # Apply filters
            if source_dataset_id and metadata.get("source_dataset_id") != source_dataset_id:
                continue

            if pipeline_name and metadata.get("pipeline_name") != pipeline_name:
                continue

            transformed_datasets.append(
                {
                    "entity_id": entity["_id"],
                    "name": metadata.get("suggested_name", "Unnamed"),
                    "source_dataset_id": metadata.get("source_dataset_id"),
                    "pipeline_name": metadata.get("pipeline_name"),
                    "created_at": entity.get("created_at"),
                    "n_rows": metadata.get("n_rows"),
                    "n_columns": metadata.get("n_columns"),
                    "transformations": metadata.get("transformations", []),
                }
            )

            if len(transformed_datasets) >= limit:
                break

        # Sort by creation date (newest first)
        transformed_datasets.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # Generate summary
        summary = "📊 Transformed Datasets\n\n"
        summary += f"Total Found: {len(transformed_datasets)}\n"

        if source_dataset_id:
            summary += f"Filter: Source Dataset = {source_dataset_id}\n"
        if pipeline_name:
            summary += f"Filter: Pipeline Name = {pipeline_name}\n"

        summary += "\n"

        if transformed_datasets:
            summary += "Datasets:\n"
            for idx, ds in enumerate(transformed_datasets[:20], 1):  # Show first 20
                summary += f"{idx}. {ds['name']}\n"
                summary += f"   Entity ID: {ds['entity_id']}\n"
                summary += f"   Source: {ds['source_dataset_id'] or 'Unknown'}\n"
                summary += f"   Pipeline: {ds['pipeline_name'] or 'Unknown'}\n"
                summary += f"   Size: {ds['n_rows']:,} rows × {ds['n_columns']} columns\n"
                if ds["transformations"]:
                    summary += f"   Transformations: {', '.join(ds['transformations'][:3])}"
                    if len(ds["transformations"]) > 3:
                        summary += f" (+{len(ds['transformations']) - 3} more)"
                    summary += "\n"
                summary += "\n"

            if len(transformed_datasets) > 20:
                summary += f"... and {len(transformed_datasets) - 20} more\n"
        else:
            summary += "No transformed datasets found matching the criteria.\n"

        return ToolResponse(
            payload={"datasets": transformed_datasets},
            summary=summary,
            metadata={
                "count": len(transformed_datasets),
                "source_dataset_id": source_dataset_id,
                "pipeline_name": pipeline_name,
            },
            storage_hint="session",
            suggested_name="transformed_datasets_list",
        )

    except Exception as e:
        logger.exception(f"Error listing transformed datasets: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error listing transformed datasets: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

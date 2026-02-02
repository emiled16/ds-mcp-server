"""Get dataset lineage showing transformation history."""

from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def get_dataset_lineage(
    dataset_id: str,
) -> str:
    """Get dataset lineage showing the transformation history.

    Traces the lineage of a dataset backward to its source and forward
    to any derived datasets. Shows the complete transformation path.

    Args:
        dataset_id: Entity ID of the dataset to trace

    Returns:
        ToolResponse with lineage information

    Example:
        "Show me the lineage of the customer_features dataset"
        → get_dataset_lineage(dataset_id="transformed_123")

        "Trace where this dataset came from"
        → get_dataset_lineage(dataset_id="final_data_456")
    """
    try:
        registry = get_repository_registry()
        repo = registry.get_repository("tool_response")

        # Get the target dataset
        entity = await registry.get("tool_response", dataset_id)

        if not entity:
            return ToolResponse(
                payload=None,
                summary=f"Error: Dataset '{dataset_id}' not found",
                metadata={"error": "NotFound", "dataset_id": dataset_id},
                storage_hint="never",
            )

        metadata = entity.metadata or {}

        # Build lineage chain backward (to source)
        backward_chain = []
        current_id = dataset_id
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)

            current_entity = await registry.get("tool_response", current_id)
            if not current_entity:
                break

            current_metadata = current_entity.metadata or {}

            step = {
                "entity_id": current_id,
                "name": current_metadata.get("suggested_name", "Unnamed"),
                "is_transformed": current_metadata.get("is_transformed_dataset", False),
                "pipeline_name": current_metadata.get("pipeline_name"),
                "transformations": current_metadata.get("transformations", []),
                "n_rows": current_metadata.get("n_rows"),
                "n_columns": current_metadata.get("n_columns"),
                "created_at": current_entity.get("created_at"),
            }

            backward_chain.append(step)

            # Move to source
            current_id = current_metadata.get("source_dataset_id")

        # Reverse to get source → target order
        forward_chain = list(reversed(backward_chain))

        # Try to find derived datasets (forward lineage)
        all_entities = await repo.list()
        derived_datasets = []

        for ent in all_entities:
            ent_metadata = ent.get("metadata", {})
            if ent_metadata.get("source_dataset_id") == dataset_id:
                derived_datasets.append(
                    {
                        "entity_id": ent["_id"],
                        "name": ent_metadata.get("suggested_name", "Unnamed"),
                        "pipeline_name": ent_metadata.get("pipeline_name"),
                        "transformations": ent_metadata.get("transformations", []),
                        "n_rows": ent_metadata.get("n_rows"),
                        "n_columns": ent_metadata.get("n_columns"),
                    }
                )

        # Generate summary
        summary = "📊 Dataset Lineage\n\n"
        summary += f"Target Dataset: {dataset_id}\n"
        summary += f"Lineage Depth: {len(forward_chain)}\n\n"

        if len(forward_chain) > 1:
            summary += "Transformation Path (Source → Target):\n"
            for idx, step in enumerate(forward_chain):
                prefix = "  " * idx
                arrow = "└─>" if idx > 0 else "  "

                summary += f"{prefix}{arrow} {step['name']}\n"
                summary += f"{prefix}   ID: {step['entity_id']}\n"

                if step["is_transformed"]:
                    summary += f"{prefix}   Pipeline: {step['pipeline_name'] or 'Unknown'}\n"
                    if step["transformations"]:
                        summary += f"{prefix}   Transformations: {', '.join(step['transformations'][:3])}\n"

                if step["n_rows"] and step["n_columns"]:
                    summary += f"{prefix}   Size: {step['n_rows']:,} rows × {step['n_columns']} columns\n"

                summary += "\n"
        else:
            summary += "This is a source dataset (no upstream transformations).\n\n"

        if derived_datasets:
            summary += f"Derived Datasets ({len(derived_datasets)}):\n"
            for ds in derived_datasets[:10]:
                summary += f"  • {ds['name']} (ID: {ds['entity_id']})\n"
                if ds["pipeline_name"]:
                    summary += f"    Pipeline: {ds['pipeline_name']}\n"
            if len(derived_datasets) > 10:
                summary += f"  ... and {len(derived_datasets) - 10} more\n"
        else:
            summary += "No derived datasets found (no downstream transformations).\n"

        result_data = {
            "dataset_id": dataset_id,
            "upstream_chain": forward_chain,
            "downstream_datasets": derived_datasets,
            "is_source": len(forward_chain) == 1,
            "depth": len(forward_chain),
        }

        return ToolResponse(
            payload=result_data,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "lineage_depth": len(forward_chain),
                "n_derived": len(derived_datasets),
            },
            storage_hint="session",
            suggested_name=f"lineage_{dataset_id}",
        )

    except Exception as e:
        logger.exception(f"Error getting dataset lineage: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error getting dataset lineage: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

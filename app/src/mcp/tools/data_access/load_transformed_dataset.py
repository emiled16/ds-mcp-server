"""Load transformed datasets by name or pipeline."""

import pandas as pd
from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def load_transformed_dataset(
    name: str | None = None,
    pipeline_name: str | None = None,
    source_dataset_id: str | None = None,
    most_recent: bool = True,
) -> str:
    """Load a transformed dataset by name, pipeline, or source.

    Searches for transformed datasets matching the criteria and loads
    the most recent one (or all matches if most_recent=False).

    Args:
        name: Optional dataset name (partial match supported)
        pipeline_name: Optional pipeline name (exact match)
        source_dataset_id: Optional source dataset ID (exact match)
        most_recent: If multiple matches, return only the most recent (default: True)

    Returns:
        ToolResponse with the loaded dataset

    Example:
        "Load the customer features dataset"
        → load_transformed_dataset(name="customer_features")

        "Load the most recent dataset from the preprocessing pipeline"
        → load_transformed_dataset(pipeline_name="preprocessing")

        "Get the latest transformed version of this data"
        → load_transformed_dataset(source_dataset_id="raw_data_123")
    """
    try:
        if not name and not pipeline_name and not source_dataset_id:
            return ToolResponse(
                payload=None,
                summary="Error: Must provide at least one search criterion (name, pipeline_name, or source_dataset_id)",
                metadata={"error": "ValidationError"},
                storage_hint="never",
            )

        registry = get_repository_registry()
        repo = registry.get_repository("tool_response")

        # Get all tool responses
        all_entities = await repo.list()

        # Filter for transformed datasets matching criteria
        matches = []

        for entity in all_entities:
            metadata = entity.get("metadata", {})

            # Check if this is a transformed dataset
            is_transformed = metadata.get("is_transformed_dataset", False)
            if not is_transformed:
                continue

            # Apply filters
            if name:
                dataset_name = metadata.get("suggested_name", "")
                if name.lower() not in dataset_name.lower():
                    continue

            if pipeline_name:
                if metadata.get("pipeline_name") != pipeline_name:
                    continue

            if source_dataset_id:
                if metadata.get("source_dataset_id") != source_dataset_id:
                    continue

            matches.append(entity)

        if not matches:
            search_criteria = []
            if name:
                search_criteria.append(f"name='{name}'")
            if pipeline_name:
                search_criteria.append(f"pipeline='{pipeline_name}'")
            if source_dataset_id:
                search_criteria.append(f"source='{source_dataset_id}'")

            return ToolResponse(
                payload=None,
                summary=f"No transformed datasets found matching: {', '.join(search_criteria)}",
                metadata={"error": "NotFound", "criteria": search_criteria},
                storage_hint="never",
            )

        # Sort by creation date (newest first)
        matches.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # Select dataset(s) to return
        if most_recent:
            selected_entity = matches[0]
            entity_id = selected_entity["_id"]

            # Load the actual dataset
            loaded_entity = await registry.get("tool_response", entity_id)
            if not loaded_entity:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Could not load dataset '{entity_id}'",
                    metadata={"error": "LoadError", "entity_id": entity_id},
                    storage_hint="never",
                )

            df = loaded_entity.payload
            if not isinstance(df, pd.DataFrame):
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Entity '{entity_id}' is not a DataFrame",
                    metadata={"error": "TypeError", "entity_id": entity_id},
                    storage_hint="never",
                )

            metadata = loaded_entity.metadata or {}

            # Generate summary
            summary = "📊 Loaded Transformed Dataset\n\n"
            summary += f"Name: {metadata.get('suggested_name', 'Unnamed')}\n"
            summary += f"Entity ID: {entity_id}\n"
            summary += f"Source Dataset: {metadata.get('source_dataset_id', 'Unknown')}\n"
            summary += f"Pipeline: {metadata.get('pipeline_name', 'Unknown')}\n"
            summary += f"Size: {len(df):,} rows × {len(df.columns)} columns\n"

            transformations = metadata.get("transformations", [])
            if transformations:
                summary += f"Transformations ({len(transformations)}):\n"
                for trans in transformations[:10]:
                    summary += f"  • {trans}\n"
                if len(transformations) > 10:
                    summary += f"  ... and {len(transformations) - 10} more\n"

            summary += "\nColumns:\n"
            for col in list(df.columns)[:20]:
                summary += f"  • {col} ({df[col].dtype})\n"
            if len(df.columns) > 20:
                summary += f"  ... and {len(df.columns) - 20} more\n"

            if len(matches) > 1:
                summary += f"\nNote: Found {len(matches)} matching datasets. Loaded the most recent.\n"

            return ToolResponse(
                payload=df,
                summary=summary,
                metadata={
                    "entity_id": entity_id,
                    "name": metadata.get("suggested_name"),
                    "source_dataset_id": metadata.get("source_dataset_id"),
                    "pipeline_name": metadata.get("pipeline_name"),
                    "n_matches": len(matches),
                },
                storage_hint="session",
                suggested_name=metadata.get("suggested_name", "transformed_dataset"),
            )

        # Return info about all matches
        summary = f"📊 Found {len(matches)} Transformed Datasets\n\n"

        for idx, match in enumerate(matches[:20], 1):
            match_metadata = match.get("metadata", {})
            summary += f"{idx}. {match_metadata.get('suggested_name', 'Unnamed')}\n"
            summary += f"   Entity ID: {match['_id']}\n"
            summary += f"   Source: {match_metadata.get('source_dataset_id', 'Unknown')}\n"
            summary += f"   Pipeline: {match_metadata.get('pipeline_name', 'Unknown')}\n"
            summary += f"   Size: {match_metadata.get('n_rows', '?'):,} rows × {match_metadata.get('n_columns', '?')} columns\n"
            summary += f"   Created: {match.get('created_at', 'Unknown')}\n\n"

        if len(matches) > 20:
            summary += f"... and {len(matches) - 20} more\n"

        summary += "\nTip: Use most_recent=True to load the most recent dataset automatically.\n"

        return ToolResponse(
            payload={"matches": [{"entity_id": m["_id"], "metadata": m.get("metadata", {})} for m in matches]},
            summary=summary,
            metadata={
                "n_matches": len(matches),
                "search_criteria": {
                    "name": name,
                    "pipeline_name": pipeline_name,
                    "source_dataset_id": source_dataset_id,
                },
            },
            storage_hint="session",
            suggested_name="dataset_search_results",
        )

    except Exception as e:
        logger.exception(f"Error loading transformed dataset: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error loading transformed dataset: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

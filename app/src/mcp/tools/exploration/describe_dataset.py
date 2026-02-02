"""Describe dataset tool."""

import pandas as pd

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def describe_dataset(entity_id: str, include_all: bool = False) -> str:
    """Get statistical summary of a dataset.

    Provides descriptive statistics including count, mean, std, min, max, and quartiles
    for numeric columns, and count, unique, top, freq for categorical columns.

    Args:
        entity_id: Entity ID of the dataset to describe
        include_all: If True, include all columns (default: only numeric)

    Returns:
        ToolResponse with statistical summary

    Example:
        "Describe the dataset abc123"
        → describe_dataset(entity_id="abc123")

        "Show full statistics including categorical columns"
        → describe_dataset(entity_id="abc123", include_all=True)
    """
    try:
        registry = get_repository_registry()
        entity = await registry.get("tool_response", entity_id)

        if not entity:
            return ToolResponse(
                payload=None,
                summary=f"Error: Dataset '{entity_id}' not found.",
                metadata={"error": "NotFound", "entity_id": entity_id},
                storage_hint="never",
            )

        df = entity.payload
        if not isinstance(df, pd.DataFrame):
            return ToolResponse(
                payload=None,
                summary=f"Error: Entity '{entity_id}' is not a DataFrame.",
                metadata={"error": "TypeError", "entity_id": entity_id},
                storage_hint="never",
            )

        # Generate statistics
        if include_all:
            stats = df.describe(include="all")
        else:
            stats = df.describe()

        # Convert stats to string for summary
        stats_str = stats.to_string(max_cols=10)

        # Additional insights
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

        # Calculate additional statistics
        null_counts = df.isnull().sum()
        null_pct = (null_counts / len(df) * 100).round(2)
        cols_with_nulls = null_counts[null_counts > 0]

        summary = f"Dataset Statistics for '{entity_id}':\n\n"
        summary += f"Shape: {df.shape[0]:,} rows × {df.shape[1]} columns\n"
        summary += f"Numeric columns: {len(numeric_cols)}\n"
        summary += f"Categorical columns: {len(categorical_cols)}\n\n"

        if len(cols_with_nulls) > 0:
            summary += "Columns with missing values:\n"
            for col in cols_with_nulls.index[:5]:
                summary += f"  • {col}: {null_counts[col]:,} ({null_pct[col]:.1f}%)\n"
            if len(cols_with_nulls) > 5:
                summary += f"  ... and {len(cols_with_nulls) - 5} more\n"
            summary += "\n"

        summary += "Descriptive Statistics:\n"
        summary += stats_str

        return ToolResponse(
            payload={
                "statistics": stats.to_dict(),
                "null_counts": null_counts.to_dict(),
                "null_percentages": null_pct.to_dict(),
            },
            summary=summary,
            metadata={
                "entity_id": entity_id,
                "shape": df.shape,
                "numeric_columns": numeric_cols,
                "categorical_columns": categorical_cols,
                "columns_with_nulls": cols_with_nulls.index.tolist(),
            },
            storage_hint="session",
            suggested_name=f"{entity.suggested_name or 'dataset'}_stats",
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error describing dataset: {e}",
            metadata={"error": type(e).__name__, "entity_id": entity_id},
            storage_hint="never",
        )

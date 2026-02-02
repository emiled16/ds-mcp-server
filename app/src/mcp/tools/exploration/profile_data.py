"""Comprehensive data profiling tool."""

import pandas as pd

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


def _get_column_profile(series: pd.Series) -> dict:
    """Generate profile for a single column."""
    profile = {
        "dtype": str(series.dtype),
        "count": len(series),
        "null_count": int(series.isnull().sum()),
        "null_pct": round(series.isnull().mean() * 100, 2),
        "unique_count": int(series.nunique()),
        "unique_pct": round(series.nunique() / len(series) * 100, 2) if len(series) > 0 else 0,
    }

    # Add numeric statistics
    if pd.api.types.is_numeric_dtype(series):
        profile.update(
            {
                "mean": round(series.mean(), 4) if not series.empty else None,
                "std": round(series.std(), 4) if not series.empty else None,
                "min": series.min() if not series.empty else None,
                "max": series.max() if not series.empty else None,
                "median": series.median() if not series.empty else None,
                "zeros_count": int((series == 0).sum()),
                "negative_count": int((series < 0).sum()),
            }
        )
    # Add categorical statistics
    elif pd.api.types.is_string_dtype(series) or series.dtype == "object":
        value_counts = series.value_counts()
        profile.update(
            {
                "top_values": value_counts.head(5).to_dict(),
                "avg_length": round(series.dropna().astype(str).str.len().mean(), 1),
                "min_length": int(series.dropna().astype(str).str.len().min()) if not series.dropna().empty else 0,
                "max_length": int(series.dropna().astype(str).str.len().max()) if not series.dropna().empty else 0,
            }
        )

    return profile


@mcp.tool
@process_tool
@register_tool
async def profile_data(entity_id: str, columns: list[str] | None = None) -> str:
    """Comprehensive data profiling including distributions, missing values, and outliers.

    Analyzes each column (or specified columns) to provide:
    - Data type and memory usage
    - Missing value analysis
    - Unique value counts
    - Statistical measures for numeric columns
    - Top values for categorical columns

    Args:
        entity_id: Entity ID of the dataset to profile
        columns: Optional list of specific columns to profile (default: all)

    Returns:
        ToolResponse with detailed profiling results

    Example:
        "Profile the dataset abc123"
        → profile_data(entity_id="abc123")

        "Profile only the price and category columns"
        → profile_data(entity_id="abc123", columns=["price", "category"])
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

        # Select columns to profile
        if columns:
            missing_cols = [c for c in columns if c not in df.columns]
            if missing_cols:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Columns not found: {missing_cols}",
                    metadata={"error": "ColumnNotFound", "missing": missing_cols},
                    storage_hint="never",
                )
            profile_cols = columns
        else:
            profile_cols = df.columns.tolist()

        # Generate profiles
        profiles = {}
        for col in profile_cols:
            profiles[col] = _get_column_profile(df[col])

        # Generate summary
        total_nulls = df[profile_cols].isnull().sum().sum()
        total_cells = len(df) * len(profile_cols)
        null_pct = round(total_nulls / total_cells * 100, 2) if total_cells > 0 else 0

        memory_mb = df[profile_cols].memory_usage(deep=True).sum() / 1024**2

        summary = f"Data Profile for '{entity_id}':\n\n"
        summary += f"Dataset Shape: {len(df):,} rows × {len(profile_cols)} columns profiled\n"
        summary += f"Total Missing Values: {total_nulls:,} ({null_pct}%)\n"
        summary += f"Memory Usage: {memory_mb:.2f} MB\n\n"

        # Add column summaries
        summary += "Column Profiles:\n"
        summary += "-" * 60 + "\n"

        for col in profile_cols[:10]:  # Show first 10 columns
            p = profiles[col]
            summary += f"\n{col} ({p['dtype']}):\n"
            summary += f"  • Non-null: {p['count'] - p['null_count']:,} ({100 - p['null_pct']:.1f}%)\n"
            summary += f"  • Unique: {p['unique_count']:,} ({p['unique_pct']:.1f}%)\n"

            if "mean" in p:
                summary += f"  • Mean: {p['mean']}, Std: {p['std']}\n"
                summary += f"  • Range: [{p['min']}, {p['max']}]\n"
            elif "top_values" in p:
                top = list(p["top_values"].items())[:3]
                top_str = ", ".join([f"'{k}': {v}" for k, v in top])
                summary += f"  • Top values: {top_str}\n"

        if len(profile_cols) > 10:
            summary += f"\n... and {len(profile_cols) - 10} more columns\n"

        return ToolResponse(
            payload=profiles,
            summary=summary,
            metadata={
                "entity_id": entity_id,
                "columns_profiled": profile_cols,
                "total_null_percentage": null_pct,
                "memory_mb": memory_mb,
            },
            storage_hint="session",
            suggested_name=f"{entity.suggested_name or 'dataset'}_profile",
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error profiling data: {e}",
            metadata={"error": type(e).__name__, "entity_id": entity_id},
            storage_hint="never",
        )

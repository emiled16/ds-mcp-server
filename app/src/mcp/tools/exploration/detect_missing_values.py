"""Missing value detection tool."""

import pandas as pd

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def detect_missing_values(
    entity_id: str,
    threshold_pct: float = 0.0,
) -> str:
    """Analyze missing values in the dataset.

    Provides detailed analysis of null/missing values including:
    - Count and percentage per column
    - Patterns of missingness
    - Recommendations for handling

    Args:
        entity_id: Entity ID of the dataset to analyze
        threshold_pct: Minimum percentage to include in report (default: 0 = all)

    Returns:
        ToolResponse with missing value analysis

    Example:
        "Check for missing values in dataset abc123"
        → detect_missing_values(entity_id="abc123")

        "Show only columns with >5% missing"
        → detect_missing_values(entity_id="abc123", threshold_pct=5.0)
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

        # Calculate missing values
        total_rows = len(df)
        null_counts = df.isnull().sum()
        null_pcts = (null_counts / total_rows * 100).round(2)

        # Create detailed analysis
        analysis = pd.DataFrame(
            {
                "null_count": null_counts,
                "null_percentage": null_pcts,
                "dtype": df.dtypes.astype(str),
            }
        )

        # Filter by threshold
        analysis_filtered = analysis[analysis["null_percentage"] >= threshold_pct]
        analysis_filtered = analysis_filtered.sort_values("null_percentage", ascending=False)

        # Calculate overall statistics
        total_nulls = null_counts.sum()
        total_cells = total_rows * len(df.columns)
        overall_null_pct = round(total_nulls / total_cells * 100, 2) if total_cells > 0 else 0

        cols_with_nulls = (null_counts > 0).sum()
        complete_cols = len(df.columns) - cols_with_nulls

        # Generate summary
        summary = f"Missing Value Analysis for '{entity_id}':\n\n"
        summary += f"Dataset Shape: {total_rows:,} rows × {len(df.columns)} columns\n"
        summary += f"Total Missing Values: {total_nulls:,} ({overall_null_pct}% of all cells)\n"
        summary += f"Columns with Missing: {cols_with_nulls} / {len(df.columns)}\n"
        summary += f"Complete Columns: {complete_cols}\n\n"

        if len(analysis_filtered) > 0:
            summary += f"Columns with ≥{threshold_pct}% missing values:\n"
            summary += "-" * 55 + "\n"
            summary += f"{'Column':<25} {'Missing':>10} {'Percent':>10} {'Type':<10}\n"
            summary += "-" * 55 + "\n"

            for col in analysis_filtered.head(20).index:
                row = analysis_filtered.loc[col]
                summary += (
                    f"{col[:25]:<25} {int(row['null_count']):>10,} {row['null_percentage']:>9.1f}% {row['dtype']:<10}\n"
                )

            if len(analysis_filtered) > 20:
                summary += f"... and {len(analysis_filtered) - 20} more columns\n"

            # Add recommendations
            summary += "\nRecommendations:\n"

            high_missing = analysis_filtered[analysis_filtered["null_percentage"] > 50]
            if len(high_missing) > 0:
                summary += f"  ⚠️ {len(high_missing)} columns have >50% missing - consider dropping\n"

            moderate_missing = analysis_filtered[
                (analysis_filtered["null_percentage"] > 5) & (analysis_filtered["null_percentage"] <= 50)
            ]
            if len(moderate_missing) > 0:
                summary += f"  • {len(moderate_missing)} columns have 5-50% missing - consider imputation\n"

            low_missing = analysis_filtered[
                (analysis_filtered["null_percentage"] > 0) & (analysis_filtered["null_percentage"] <= 5)
            ]
            if len(low_missing) > 0:
                summary += f"  • {len(low_missing)} columns have <5% missing - simple imputation likely sufficient\n"

        elif threshold_pct > 0:
            summary += f"No columns have ≥{threshold_pct}% missing values.\n"
        else:
            summary += "No missing values found in the dataset! ✓\n"

        # Check for rows with all nulls
        all_null_rows = df.isnull().all(axis=1).sum()
        if all_null_rows > 0:
            summary += f"\n⚠️ Found {all_null_rows:,} completely empty rows.\n"

        return ToolResponse(
            payload={
                "analysis": analysis.to_dict(),
                "summary_stats": {
                    "total_rows": total_rows,
                    "total_columns": len(df.columns),
                    "total_nulls": int(total_nulls),
                    "overall_null_pct": overall_null_pct,
                    "cols_with_nulls": int(cols_with_nulls),
                    "complete_cols": int(complete_cols),
                },
            },
            summary=summary,
            metadata={
                "entity_id": entity_id,
                "threshold_pct": threshold_pct,
                "columns_with_nulls": analysis_filtered.index.tolist(),
            },
            storage_hint="session",
            suggested_name=f"{entity.suggested_name or 'dataset'}_missing_analysis",
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error detecting missing values: {e}",
            metadata={"error": type(e).__name__, "entity_id": entity_id},
            storage_hint="never",
        )

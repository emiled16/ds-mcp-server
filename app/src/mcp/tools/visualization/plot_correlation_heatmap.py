"""Generate correlation matrix heatmaps."""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry
from src.utils.plotting import close_figure, save_plot_to_minio


@mcp.tool
@process_tool
@register_tool
async def plot_correlation_heatmap(
    dataset_id: str,
    method: str = "pearson",
    annot: bool = True,
    cmap: str = "coolwarm",
    threshold: float | None = None,
) -> str:
    """Generate a correlation matrix heatmap for numeric columns.

    Creates a heatmap visualization showing correlations between all
    numeric columns in the dataset. Useful for identifying relationships
    between features.

    Args:
        dataset_id: Entity ID of the dataset
        method: Correlation method - "pearson", "spearman", or "kendall" (default: "pearson")
        annot: Whether to annotate cells with correlation values (default: True)
        cmap: Colormap name (default: "coolwarm")
        threshold: Optional correlation threshold to highlight strong correlations

    Returns:
        ToolResponse with heatmap plot and correlation matrix

    Example:
        "Show correlation heatmap for the features dataset"
        → plot_correlation_heatmap(dataset_id="features_123")

        "Generate Spearman correlation heatmap with threshold"
        → plot_correlation_heatmap(
            dataset_id="data_123",
            method="spearman",
            threshold=0.7
        )
    """
    try:
        # Get dataset
        registry = get_repository_registry()
        entity = await registry.get("tool_response", dataset_id)

        if not entity:
            return ToolResponse(
                payload=None,
                summary=f"Error: Dataset '{dataset_id}' not found",
                metadata={"error": "NotFound", "dataset_id": dataset_id},
                storage_hint="never",
            )

        df = entity.payload
        if not isinstance(df, pd.DataFrame):
            return ToolResponse(
                payload=None,
                summary=f"Error: Entity '{dataset_id}' is not a DataFrame",
                metadata={"error": "TypeError", "entity_id": dataset_id},
                storage_hint="never",
            )

        # Select numeric columns only
        numeric_df = df.select_dtypes(include=["number"])

        if numeric_df.empty or len(numeric_df.columns) < 2:
            return ToolResponse(
                payload=None,
                summary="Error: Need at least 2 numeric columns for correlation analysis",
                metadata={"error": "InsufficientColumns"},
                storage_hint="never",
            )

        logger.info(f"Computing {method} correlation matrix for {len(numeric_df.columns)} columns")

        # Compute correlation matrix
        corr_matrix = numeric_df.corr(method=method)

        # Create heatmap
        fig, ax = plt.subplots(figsize=(max(10, len(numeric_df.columns) * 0.8), max(8, len(numeric_df.columns) * 0.7)))

        # Generate mask for upper triangle if there are many features
        mask = None
        if len(numeric_df.columns) > 10:
            import numpy as np

            mask = np.triu(np.ones_like(corr_matrix, dtype=bool))

        # Create heatmap
        sns.heatmap(
            corr_matrix,
            annot=annot if len(numeric_df.columns) <= 20 else False,  # Too cluttered with many features
            fmt=".2f",
            cmap=cmap,
            center=0,
            square=True,
            linewidths=0.5,
            cbar_kws={"shrink": 0.8, "label": "Correlation"},
            mask=mask,
            ax=ax,
        )

        ax.set_title(f"Correlation Matrix ({method.title()})")
        plt.tight_layout()

        # Save plot
        object_key, plot_url = save_plot_to_minio(fig, f"correlation_{method}")
        close_figure(fig)

        # Find strong correlations
        strong_correlations = []
        if threshold is not None:
            for i in range(len(corr_matrix.columns)):
                for j in range(i + 1, len(corr_matrix.columns)):
                    corr_value = corr_matrix.iloc[i, j]
                    if abs(corr_value) >= threshold:
                        strong_correlations.append(
                            {
                                "feature1": corr_matrix.columns[i],
                                "feature2": corr_matrix.columns[j],
                                "correlation": float(corr_value),
                            }
                        )

            # Sort by absolute correlation
            strong_correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)

        # Generate summary
        summary = "📊 Correlation Heatmap\n\n"
        summary += f"Method: {method.title()}\n"
        summary += f"Numeric Columns: {len(numeric_df.columns)}\n\n"

        if threshold is not None:
            summary += f"Strong Correlations (|r| >= {threshold}):\n"
            if strong_correlations:
                for corr in strong_correlations[:15]:  # Show top 15
                    summary += f"  • {corr['feature1']} ↔ {corr['feature2']}: {corr['correlation']:+.3f}\n"
                if len(strong_correlations) > 15:
                    summary += f"  ... and {len(strong_correlations) - 15} more\n"
            else:
                summary += f"  No correlations exceed threshold of {threshold}\n"
            summary += "\n"

        # Top positive correlations
        corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_pairs.append(
                    {
                        "feature1": corr_matrix.columns[i],
                        "feature2": corr_matrix.columns[j],
                        "correlation": float(corr_matrix.iloc[i, j]),
                    }
                )

        if corr_pairs:
            # Top positive
            top_positive = sorted(corr_pairs, key=lambda x: x["correlation"], reverse=True)[:5]
            summary += "Top Positive Correlations:\n"
            for corr in top_positive:
                if corr["correlation"] > 0:
                    summary += f"  • {corr['feature1']} ↔ {corr['feature2']}: {corr['correlation']:+.3f}\n"

            # Top negative
            top_negative = sorted(corr_pairs, key=lambda x: x["correlation"])[:5]
            summary += "\nTop Negative Correlations:\n"
            for corr in top_negative:
                if corr["correlation"] < 0:
                    summary += f"  • {corr['feature1']} ↔ {corr['feature2']}: {corr['correlation']:+.3f}\n"

        summary += f"\n🖼️ Plot URL: {plot_url}\n"

        result_data = {
            "correlation_matrix": corr_matrix.to_dict(),
            "method": method,
            "n_features": len(numeric_df.columns),
            "strong_correlations": strong_correlations if threshold else None,
            "threshold": threshold,
            "plot_url": plot_url,
            "plot_object_key": object_key,
        }

        return ToolResponse(
            payload=result_data,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "method": method,
                "n_features": len(numeric_df.columns),
            },
            storage_hint="session",
            suggested_name=f"correlation_{method}",
        )

    except Exception as e:
        logger.exception(f"Error plotting correlation heatmap: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error plotting correlation heatmap: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

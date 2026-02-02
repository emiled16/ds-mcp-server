"""Correlation analysis tool."""

import pandas as pd

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def analyze_correlations(
    entity_id: str,
    target: str | None = None,
    method: str = "pearson",
    threshold: float = 0.3,
) -> str:
    """Analyze correlations between numeric columns in the dataset.

    Computes correlation matrix and identifies strongly correlated pairs.
    Optionally focuses on correlations with a specific target column.

    Args:
        entity_id: Entity ID of the dataset
        target: Optional target column to focus correlations on
        method: Correlation method ('pearson', 'spearman', 'kendall')
        threshold: Minimum absolute correlation to highlight (default: 0.3)

    Returns:
        ToolResponse with correlation matrix and insights

    Example:
        "Analyze correlations in dataset abc123"
        → analyze_correlations(entity_id="abc123")

        "Find features correlated with sales"
        → analyze_correlations(entity_id="abc123", target="sales")

        "Use Spearman correlation with 0.5 threshold"
        → analyze_correlations(entity_id="abc123", method="spearman", threshold=0.5)
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

        # Validate method
        valid_methods = ["pearson", "spearman", "kendall"]
        if method not in valid_methods:
            return ToolResponse(
                payload=None,
                summary=f"Error: Invalid method '{method}'. Use one of: {valid_methods}",
                metadata={"error": "ValueError", "valid_methods": valid_methods},
                storage_hint="never",
            )

        # Get numeric columns
        numeric_df = df.select_dtypes(include=["number"])
        if numeric_df.empty:
            return ToolResponse(
                payload=None,
                summary="Error: No numeric columns found in dataset.",
                metadata={"error": "NoNumericColumns"},
                storage_hint="never",
            )

        # Validate target column
        if target and target not in numeric_df.columns:
            if target in df.columns:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Target column '{target}' is not numeric.",
                    metadata={"error": "NonNumericTarget", "target": target},
                    storage_hint="never",
                )
            return ToolResponse(
                payload=None,
                summary=f"Error: Target column '{target}' not found.",
                metadata={"error": "ColumnNotFound", "target": target},
                storage_hint="never",
            )

        # Compute correlation matrix
        corr_matrix = numeric_df.corr(method=method)

        # Generate insights
        summary = f"Correlation Analysis for '{entity_id}' ({method} method):\n\n"
        summary += f"Analyzed {len(numeric_df.columns)} numeric columns\n"
        summary += f"Threshold for highlighting: |r| >= {threshold}\n\n"

        if target:
            # Focus on target correlations
            target_corr = corr_matrix[target].drop(target).sort_values(key=abs, ascending=False)

            summary += f"Correlations with '{target}':\n"
            summary += "-" * 50 + "\n"

            strong_corrs = target_corr[abs(target_corr) >= threshold]
            if len(strong_corrs) > 0:
                for col, corr in strong_corrs.head(15).items():
                    strength = "Strong" if abs(corr) >= 0.7 else "Moderate"
                    direction = "positive" if corr > 0 else "negative"
                    summary += f"  • {col}: {corr:.3f} ({strength} {direction})\n"
            else:
                summary += f"  No correlations above {threshold} threshold\n"

            # Weak correlations (potential feature engineering opportunities)
            weak_corrs = target_corr[abs(target_corr) < 0.1]
            if len(weak_corrs) > 0:
                summary += f"\nWeakly correlated features ({len(weak_corrs)}):\n"
                for col in weak_corrs.head(5).index:
                    summary += f"  • {col}: {target_corr[col]:.3f}\n"
        else:
            # General correlation analysis
            # Find strong correlations (excluding self-correlations)
            strong_pairs = []
            for i, col1 in enumerate(corr_matrix.columns):
                for col2 in corr_matrix.columns[i + 1 :]:
                    corr = corr_matrix.loc[col1, col2]
                    if abs(corr) >= threshold:
                        strong_pairs.append((col1, col2, corr))

            strong_pairs.sort(key=lambda x: abs(x[2]), reverse=True)

            summary += "Strongly Correlated Pairs:\n"
            summary += "-" * 50 + "\n"

            if strong_pairs:
                for col1, col2, corr in strong_pairs[:15]:
                    strength = "Very strong" if abs(corr) >= 0.8 else "Strong" if abs(corr) >= 0.6 else "Moderate"
                    summary += f"  • {col1} ↔ {col2}: {corr:.3f} ({strength})\n"

                # Warning about multicollinearity
                very_strong = [p for p in strong_pairs if abs(p[2]) >= 0.8]
                if very_strong:
                    summary += f"\n⚠️ Warning: {len(very_strong)} pairs have very high correlation (>0.8).\n"
                    summary += "   Consider removing redundant features to avoid multicollinearity.\n"
            else:
                summary += f"  No pairs with correlation above {threshold}\n"

        # Add matrix preview for small datasets
        if len(numeric_df.columns) <= 8:
            summary += f"\nCorrelation Matrix:\n{corr_matrix.round(2).to_string()}"

        return ToolResponse(
            payload={
                "correlation_matrix": corr_matrix.to_dict(),
                "method": method,
                "threshold": threshold,
                "target": target,
            },
            summary=summary,
            metadata={
                "entity_id": entity_id,
                "numeric_columns": numeric_df.columns.tolist(),
                "method": method,
                "target": target,
            },
            storage_hint="session",
            suggested_name=f"{entity.suggested_name or 'dataset'}_correlations",
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error analyzing correlations: {e}",
            metadata={"error": type(e).__name__, "entity_id": entity_id},
            storage_hint="never",
        )

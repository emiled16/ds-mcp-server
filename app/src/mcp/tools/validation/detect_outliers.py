"""Statistical outlier detection with visualization."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import IsolationForest

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry
from src.utils.plotting import close_figure, save_plot_to_minio


@mcp.tool
@process_tool
@register_tool
async def detect_outliers(
    dataset_id: str,
    method: str = "iqr",
    threshold: float = 3.0,
    columns: list[str] | None = None,
    generate_plot: bool = True,
) -> str:
    """Detect statistical outliers in numeric data.

    Supports multiple detection methods:
    - IQR (Interquartile Range): Values outside Q1-1.5*IQR or Q3+1.5*IQR
    - Z-score: Values more than N standard deviations from mean
    - Isolation Forest: ML-based anomaly detection

    Args:
        dataset_id: Entity ID of the dataset
        method: Detection method - "iqr", "zscore", or "isolation_forest" (default: "iqr")
        threshold: Threshold for detection (default: 3.0)
            - IQR: multiplier for IQR (typically 1.5 or 3.0)
            - Z-score: number of standard deviations (typically 2.5 or 3.0)
            - Isolation Forest: contamination rate (0.0-0.5)
        columns: Optional list of columns to check (defaults to all numeric)
        generate_plot: Whether to generate box plots (default: True)

    Returns:
        ToolResponse with outlier detection results and optional plot

    Example:
        "Detect outliers in the sales data using IQR method"
        → detect_outliers(dataset_id="sales_data_123", method="iqr")

        "Find outliers using Z-score with threshold 2.5"
        → detect_outliers(
            dataset_id="metrics_data_123",
            method="zscore",
            threshold=2.5
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

        # Select numeric columns
        if columns is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        else:
            numeric_cols = [col for col in columns if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]

        if not numeric_cols:
            return ToolResponse(
                payload=None,
                summary="Error: No numeric columns found for outlier detection",
                metadata={"error": "NoNumericColumns"},
                storage_hint="never",
            )

        logger.info(f"Detecting outliers using {method} method on {len(numeric_cols)} columns")

        outlier_results = {}
        total_outliers = 0

        for col in numeric_cols:
            col_data = df[col].dropna()

            if len(col_data) == 0:
                continue

            if method == "iqr":
                # IQR method
                Q1 = col_data.quantile(0.25)
                Q3 = col_data.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR

                outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
                outlier_indices = df[outlier_mask].index.tolist()
                outlier_values = df.loc[outlier_mask, col].tolist()

                outlier_results[col] = {
                    "method": "iqr",
                    "count": len(outlier_indices),
                    "percentage": len(outlier_indices) / len(df) * 100,
                    "lower_bound": float(lower_bound),
                    "upper_bound": float(upper_bound),
                    "outlier_indices": outlier_indices[:100],  # Limit to 100
                    "outlier_values": [float(v) for v in outlier_values[:100]],
                    "Q1": float(Q1),
                    "Q3": float(Q3),
                    "IQR": float(IQR),
                }

            elif method == "zscore":
                # Z-score method
                mean = col_data.mean()
                std = col_data.std()

                if std == 0:
                    outlier_results[col] = {
                        "method": "zscore",
                        "count": 0,
                        "percentage": 0.0,
                        "note": "Zero standard deviation",
                    }
                    continue

                z_scores = np.abs((df[col] - mean) / std)
                outlier_mask = z_scores > threshold
                outlier_indices = df[outlier_mask].index.tolist()
                outlier_values = df.loc[outlier_mask, col].tolist()

                outlier_results[col] = {
                    "method": "zscore",
                    "count": len(outlier_indices),
                    "percentage": len(outlier_indices) / len(df) * 100,
                    "mean": float(mean),
                    "std": float(std),
                    "threshold": threshold,
                    "outlier_indices": outlier_indices[:100],
                    "outlier_values": [float(v) for v in outlier_values[:100]],
                }

            elif method == "isolation_forest":
                # Isolation Forest method
                if len(col_data) < 10:
                    outlier_results[col] = {
                        "method": "isolation_forest",
                        "count": 0,
                        "percentage": 0.0,
                        "note": "Insufficient data (< 10 samples)",
                    }
                    continue

                iso_forest = IsolationForest(contamination=min(threshold, 0.5), random_state=42)
                predictions = iso_forest.fit_predict(col_data.values.reshape(-1, 1))

                outlier_mask = predictions == -1
                outlier_mask_full = pd.Series(False, index=df.index)
                outlier_mask_full[col_data.index[outlier_mask]] = True

                outlier_indices = df[outlier_mask_full].index.tolist()
                outlier_values = df.loc[outlier_mask_full, col].tolist()

                outlier_results[col] = {
                    "method": "isolation_forest",
                    "count": len(outlier_indices),
                    "percentage": len(outlier_indices) / len(df) * 100,
                    "contamination": threshold,
                    "outlier_indices": outlier_indices[:100],
                    "outlier_values": [float(v) for v in outlier_values[:100]],
                }

            else:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Unknown method '{method}'. Use 'iqr', 'zscore', or 'isolation_forest'",
                    metadata={"error": "InvalidMethod", "method": method},
                    storage_hint="never",
                )

            total_outliers += outlier_results[col]["count"]

        # Generate plot if requested
        plot_url = None
        plot_object_key = None

        if generate_plot and numeric_cols:
            n_cols = min(len(numeric_cols), 4)
            n_rows = (len(numeric_cols) + n_cols - 1) // n_cols

            fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows))
            if n_rows == 1 and n_cols == 1:
                axes = [axes]
            elif n_rows == 1 or n_cols == 1:
                axes = axes
            else:
                axes = axes.flatten()

            for idx, col in enumerate(numeric_cols):
                ax = axes[idx] if len(numeric_cols) > 1 else axes[0]

                # Box plot
                df[col].plot(kind="box", ax=ax)
                ax.set_title(f"{col}\n({outlier_results[col]['count']} outliers)")
                ax.set_ylabel("Value")
                ax.grid(alpha=0.3)

            # Hide unused subplots
            for idx in range(len(numeric_cols), len(axes)):
                axes[idx].set_visible(False)

            plt.tight_layout()
            plot_object_key, plot_url = save_plot_to_minio(fig, f"outliers_{method}")
            close_figure(fig)

        # Generate summary
        summary = "🔍 Outlier Detection Results\n\n"
        summary += f"Method: {method.upper()}\n"
        summary += f"Threshold: {threshold}\n"
        summary += f"Columns Analyzed: {len(numeric_cols)}\n"
        summary += f"Total Outliers: {total_outliers}\n\n"

        summary += "Per-Column Results:\n"
        for col, result in outlier_results.items():
            summary += f"  • {col}: {result['count']} outliers ({result['percentage']:.2f}%)\n"

            if method == "iqr" and "lower_bound" in result:
                summary += f"    Range: [{result['lower_bound']:.2f}, {result['upper_bound']:.2f}]\n"
            elif method == "zscore" and "mean" in result:
                summary += f"    Mean: {result['mean']:.2f}, Std: {result['std']:.2f}\n"

        if plot_url:
            summary += f"\n🖼️ Plot URL: {plot_url}\n"

        result_data = {
            "method": method,
            "threshold": threshold,
            "total_outliers": total_outliers,
            "columns_analyzed": len(numeric_cols),
            "results": outlier_results,
            "plot_url": plot_url,
            "plot_object_key": plot_object_key,
        }

        return ToolResponse(
            payload=result_data,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "method": method,
                "total_outliers": total_outliers,
            },
            storage_hint="session",
            suggested_name=f"outliers_{method}",
        )

    except Exception as e:
        logger.exception(f"Error detecting outliers: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error detecting outliers: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

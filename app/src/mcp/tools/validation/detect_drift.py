"""Detect data drift by comparing distributions."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry
from src.utils.plotting import close_figure, save_plot_to_minio


@mcp.tool
@process_tool
@register_tool
async def detect_data_drift(
    reference_dataset_id: str,
    current_dataset_id: str,
    columns: list[str] | None = None,
    significance_level: float = 0.05,
    generate_plot: bool = True,
) -> str:
    """Detect data drift by comparing distributions between datasets.

    Compares the distribution of a current dataset against a reference dataset
    to detect if the data has changed significantly. Uses statistical tests:
    - Kolmogorov-Smirnov (KS) test for numeric columns
    - Chi-square test for categorical columns

    Args:
        reference_dataset_id: Entity ID of the reference (baseline) dataset
        current_dataset_id: Entity ID of the current (new) dataset
        columns: Optional list of columns to check (defaults to common columns)
        significance_level: P-value threshold for drift detection (default: 0.05)
        generate_plot: Whether to generate distribution comparison plots (default: True)

    Returns:
        ToolResponse with drift detection results

    Example:
        "Check if the new sales data has drifted from the baseline"
        → detect_data_drift(
            reference_dataset_id="sales_baseline_123",
            current_dataset_id="sales_current_456"
        )

        "Detect drift in specific columns with strict threshold"
        → detect_data_drift(
            reference_dataset_id="baseline_123",
            current_dataset_id="current_456",
            columns=["price", "quantity"],
            significance_level=0.01
        )
    """
    try:
        # Get datasets
        registry = get_repository_registry()

        ref_entity = await registry.get("tool_response", reference_dataset_id)
        if not ref_entity:
            return ToolResponse(
                payload=None,
                summary=f"Error: Reference dataset '{reference_dataset_id}' not found",
                metadata={"error": "NotFound", "dataset_id": reference_dataset_id},
                storage_hint="never",
            )

        cur_entity = await registry.get("tool_response", current_dataset_id)
        if not cur_entity:
            return ToolResponse(
                payload=None,
                summary=f"Error: Current dataset '{current_dataset_id}' not found",
                metadata={"error": "NotFound", "dataset_id": current_dataset_id},
                storage_hint="never",
            )

        ref_df = ref_entity.payload
        cur_df = cur_entity.payload

        if not isinstance(ref_df, pd.DataFrame) or not isinstance(cur_df, pd.DataFrame):
            return ToolResponse(
                payload=None,
                summary="Error: Both entities must be DataFrames",
                metadata={"error": "TypeError"},
                storage_hint="never",
            )

        # Determine columns to check
        if columns is None:
            columns = list(set(ref_df.columns) & set(cur_df.columns))

        if not columns:
            return ToolResponse(
                payload=None,
                summary="Error: No common columns found between datasets",
                metadata={"error": "NoCommonColumns"},
                storage_hint="never",
            )

        logger.info(f"Detecting drift on {len(columns)} columns between datasets")

        drift_results = {}
        drift_detected = []

        for col in columns:
            if col not in ref_df.columns or col not in cur_df.columns:
                continue

            ref_col = ref_df[col].dropna()
            cur_col = cur_df[col].dropna()

            if len(ref_col) == 0 or len(cur_col) == 0:
                drift_results[col] = {
                    "test": "skipped",
                    "reason": "Insufficient data",
                }
                continue

            # Determine test based on data type
            if pd.api.types.is_numeric_dtype(ref_df[col]):
                # Kolmogorov-Smirnov test for numeric columns
                statistic, p_value = stats.ks_2samp(ref_col, cur_col)

                drift_results[col] = {
                    "test": "kolmogorov_smirnov",
                    "statistic": float(statistic),
                    "p_value": float(p_value),
                    "drift_detected": p_value < significance_level,
                    "ref_mean": float(ref_col.mean()),
                    "cur_mean": float(cur_col.mean()),
                    "ref_std": float(ref_col.std()),
                    "cur_std": float(cur_col.std()),
                    "mean_shift": float(cur_col.mean() - ref_col.mean()),
                    "mean_shift_pct": float((cur_col.mean() - ref_col.mean()) / ref_col.mean() * 100)
                    if ref_col.mean() != 0
                    else None,
                }

                if p_value < significance_level:
                    drift_detected.append(col)

            else:
                # Chi-square test for categorical columns
                # Create frequency tables
                ref_counts = ref_col.value_counts()
                cur_counts = cur_col.value_counts()

                # Align categories
                all_categories = sorted(set(ref_counts.index) | set(cur_counts.index))

                ref_freq = [ref_counts.get(cat, 0) for cat in all_categories]
                cur_freq = [cur_counts.get(cat, 0) for cat in all_categories]

                # Chi-square test
                try:
                    statistic, p_value = stats.chisquare(cur_freq, ref_freq)

                    drift_results[col] = {
                        "test": "chi_square",
                        "statistic": float(statistic),
                        "p_value": float(p_value),
                        "drift_detected": p_value < significance_level,
                        "ref_unique_count": int(ref_col.nunique()),
                        "cur_unique_count": int(cur_col.nunique()),
                        "new_categories": list(set(cur_counts.index) - set(ref_counts.index)),
                        "missing_categories": list(set(ref_counts.index) - set(cur_counts.index)),
                    }

                    if p_value < significance_level:
                        drift_detected.append(col)

                except Exception as e:
                    drift_results[col] = {
                        "test": "chi_square",
                        "error": str(e),
                    }

        # Generate plots if requested
        plot_url = None
        plot_object_key = None

        if generate_plot and drift_detected:
            # Plot top 4 drifted columns
            plot_cols = drift_detected[:4]
            n_cols = min(len(plot_cols), 2)
            n_rows = (len(plot_cols) + 1) // 2

            fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 4 * n_rows))
            if len(plot_cols) == 1:
                axes = [axes]
            elif n_rows > 1:
                axes = axes.flatten()

            for idx, col in enumerate(plot_cols):
                ax = axes[idx] if len(plot_cols) > 1 else axes[0]

                if pd.api.types.is_numeric_dtype(ref_df[col]):
                    # Histogram comparison
                    ref_df[col].hist(ax=ax, alpha=0.5, label="Reference", bins=30, density=True)
                    cur_df[col].hist(ax=ax, alpha=0.5, label="Current", bins=30, density=True)
                else:
                    # Bar chart comparison for categorical
                    ref_counts = ref_df[col].value_counts().head(10)
                    cur_counts = cur_df[col].value_counts().head(10)

                    x = np.arange(len(ref_counts))
                    width = 0.35

                    ax.bar(x - width / 2, ref_counts.values, width, label="Reference", alpha=0.7)
                    ax.bar(x + width / 2, cur_counts.values, width, label="Current", alpha=0.7)
                    ax.set_xticks(x)
                    ax.set_xticklabels(ref_counts.index, rotation=45, ha="right")

                ax.set_title(f"{col}\n(p={drift_results[col]['p_value']:.4f})")
                ax.legend()
                ax.grid(alpha=0.3)

            plt.tight_layout()
            plot_object_key, plot_url = await save_plot_to_minio(fig, "data_drift")
            close_figure(fig)

        # Generate summary
        summary = "📊 Data Drift Detection\n\n"
        summary += f"Reference Dataset: {len(ref_df):,} rows\n"
        summary += f"Current Dataset: {len(cur_df):,} rows\n"
        summary += f"Columns Analyzed: {len(columns)}\n"
        summary += f"Significance Level: {significance_level}\n\n"

        summary += f"Drift Status: {'❌ DRIFT DETECTED' if drift_detected else '✅ NO DRIFT'}\n"
        summary += f"Columns with Drift: {len(drift_detected)}\n\n"

        if drift_detected:
            summary += "Drifted Columns:\n"
            for col in drift_detected:
                result = drift_results[col]
                summary += f"  ❌ {col} (p={result['p_value']:.4f}, test={result['test']})\n"

                if result["test"] == "kolmogorov_smirnov":
                    if result.get("mean_shift_pct") is not None:
                        summary += f"     Mean shift: {result['mean_shift_pct']:+.2f}%\n"
                elif result["test"] == "chi_square":
                    if result.get("new_categories"):
                        summary += f"     New categories: {result['new_categories'][:5]}\n"

            summary += "\n"

        # Stable columns
        stable_cols = [col for col in columns if col not in drift_detected and col in drift_results]
        if stable_cols:
            summary += f"Stable Columns ({len(stable_cols)}):\n"
            for col in stable_cols[:10]:
                result = drift_results[col]
                if "p_value" in result:
                    summary += f"  ✅ {col} (p={result['p_value']:.4f})\n"
            if len(stable_cols) > 10:
                summary += f"  ... and {len(stable_cols) - 10} more\n"
            summary += "\n"

        if plot_url:
            summary += f"🖼️ Distribution Plots: {plot_url}\n"

        result_data = {
            "drift_detected": len(drift_detected) > 0,
            "drifted_columns": drift_detected,
            "significance_level": significance_level,
            "results": drift_results,
            "n_ref_rows": len(ref_df),
            "n_cur_rows": len(cur_df),
            "plot_url": plot_url,
            "plot_object_key": plot_object_key,
        }

        return ToolResponse(
            payload=result_data,
            summary=summary,
            metadata={
                "reference_dataset_id": reference_dataset_id,
                "current_dataset_id": current_dataset_id,
                "drift_detected": len(drift_detected) > 0,
                "n_drifted": len(drift_detected),
            },
            storage_hint="session",
            suggested_name="drift_detection",
        )

    except Exception as e:
        logger.exception(f"Error detecting data drift: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error detecting data drift: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

"""Generate distribution plots for data exploration."""

import matplotlib.pyplot as plt
import pandas as pd
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
async def plot_distribution(
    dataset_id: str,
    column: str,
    plot_type: str = "auto",
    bins: int = 30,
    kde: bool = True,
) -> str:
    """Generate distribution plots for exploring data distributions.

    Creates various distribution visualizations:
    - Histogram: Shows frequency distribution
    - KDE: Kernel Density Estimate for smooth distribution
    - Box plot: Shows quartiles and outliers
    - Violin plot: Combination of box plot and KDE

    Args:
        dataset_id: Entity ID of the dataset
        column: Column name to plot
        plot_type: Type of plot - "auto", "histogram", "kde", "box", "violin", or "all" (default: "auto")
        bins: Number of bins for histogram (default: 30)
        kde: Whether to overlay KDE on histogram (default: True)

    Returns:
        ToolResponse with distribution plot and statistics

    Example:
        "Show distribution of the price column"
        → plot_distribution(dataset_id="sales_123", column="price")

        "Generate all distribution plots for age"
        → plot_distribution(
            dataset_id="customer_123",
            column="age",
            plot_type="all"
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

        # Check column exists
        if column not in df.columns:
            return ToolResponse(
                payload=None,
                summary=f"Error: Column '{column}' not found in dataset. Available: {list(df.columns)}",
                metadata={"error": "ColumnNotFound", "column": column},
                storage_hint="never",
            )

        col_data = df[column].dropna()

        if len(col_data) == 0:
            return ToolResponse(
                payload=None,
                summary=f"Error: Column '{column}' has no non-null values",
                metadata={"error": "NoData", "column": column},
                storage_hint="never",
            )

        logger.info(f"Plotting distribution for column '{column}' with {len(col_data)} values")

        # Auto-select plot type based on data type
        is_numeric = pd.api.types.is_numeric_dtype(col_data)
        n_unique = col_data.nunique()

        if plot_type == "auto":
            if is_numeric:
                if n_unique > 20:
                    plot_type = "histogram"
                else:
                    plot_type = "all"
            else:
                plot_type = "bar"

        # Compute statistics
        stats = {}
        if is_numeric:
            stats = {
                "count": len(col_data),
                "mean": float(col_data.mean()),
                "std": float(col_data.std()),
                "min": float(col_data.min()),
                "q1": float(col_data.quantile(0.25)),
                "median": float(col_data.median()),
                "q3": float(col_data.quantile(0.75)),
                "max": float(col_data.max()),
                "skewness": float(col_data.skew()),
                "kurtosis": float(col_data.kurtosis()),
            }
        else:
            value_counts = col_data.value_counts()
            stats = {
                "count": len(col_data),
                "unique": int(n_unique),
                "top_value": str(value_counts.index[0]),
                "top_frequency": int(value_counts.iloc[0]),
                "top_percentage": float(value_counts.iloc[0] / len(col_data) * 100),
            }

        # Create plots
        if plot_type == "all" and is_numeric:
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            ax1, ax2, ax3, ax4 = axes.flatten()

            # Histogram
            ax1.hist(col_data, bins=bins, edgecolor="black", alpha=0.7)
            ax1.set_xlabel(column)
            ax1.set_ylabel("Frequency")
            ax1.set_title("Histogram")
            ax1.grid(alpha=0.3)

            # KDE
            col_data.plot(kind="kde", ax=ax2, linewidth=2)
            ax2.set_xlabel(column)
            ax2.set_ylabel("Density")
            ax2.set_title("Kernel Density Estimate")
            ax2.grid(alpha=0.3)

            # Box plot
            ax3.boxplot(col_data, vert=True)
            ax3.set_ylabel(column)
            ax3.set_title("Box Plot")
            ax3.grid(alpha=0.3)

            # Violin plot
            parts = ax4.violinplot([col_data], vert=True, showmeans=True, showmedians=True)
            ax4.set_ylabel(column)
            ax4.set_title("Violin Plot")
            ax4.grid(alpha=0.3)

            fig.suptitle(f"Distribution Analysis: {column}", fontsize=14)

        elif plot_type == "histogram" or (plot_type == "auto" and is_numeric):
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(col_data, bins=bins, edgecolor="black", alpha=0.7, density=kde)

            if kde:
                # Overlay KDE
                ax2 = ax.twinx()
                col_data.plot(kind="kde", ax=ax2, color="red", linewidth=2, label="KDE")
                ax2.set_ylabel("Density", color="red")
                ax2.tick_params(axis="y", labelcolor="red")
                ax2.legend(loc="upper right")

            ax.set_xlabel(column)
            ax.set_ylabel("Frequency")
            ax.set_title(f"Distribution: {column}")
            ax.grid(alpha=0.3)

        elif plot_type == "kde" and is_numeric:
            fig, ax = plt.subplots(figsize=(10, 6))
            col_data.plot(kind="kde", ax=ax, linewidth=2, fill=True, alpha=0.5)
            ax.set_xlabel(column)
            ax.set_ylabel("Density")
            ax.set_title(f"Kernel Density Estimate: {column}")
            ax.grid(alpha=0.3)

        elif plot_type == "box" and is_numeric:
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.boxplot(col_data, vert=True)
            ax.set_ylabel(column)
            ax.set_title(f"Box Plot: {column}")
            ax.grid(alpha=0.3)

        elif plot_type == "violin" and is_numeric:
            fig, ax = plt.subplots(figsize=(8, 6))
            parts = ax.violinplot([col_data], vert=True, showmeans=True, showmedians=True, showextrema=True)
            ax.set_ylabel(column)
            ax.set_title(f"Violin Plot: {column}")
            ax.grid(alpha=0.3)

        elif plot_type == "bar" or not is_numeric:
            # Bar chart for categorical data
            fig, ax = plt.subplots(figsize=(10, 6))
            value_counts = col_data.value_counts().head(20)  # Top 20
            value_counts.plot(kind="bar", ax=ax, edgecolor="black", alpha=0.7)
            ax.set_xlabel(column)
            ax.set_ylabel("Count")
            ax.set_title(f"Value Distribution: {column}")
            ax.tick_params(axis="x", rotation=45)
            ax.grid(alpha=0.3)

        else:
            return ToolResponse(
                payload=None,
                summary=f"Error: Invalid plot_type '{plot_type}' for this data",
                metadata={"error": "InvalidPlotType", "plot_type": plot_type},
                storage_hint="never",
            )

        plt.tight_layout()

        # Save plot
        object_key, plot_url = save_plot_to_minio(fig, f"distribution_{column}")
        close_figure(fig)

        # Generate summary
        summary = f"📊 Distribution Analysis: {column}\n\n"
        summary += f"Data Type: {'Numeric' if is_numeric else 'Categorical'}\n"
        summary += f"Plot Type: {plot_type.title()}\n\n"

        summary += "Statistics:\n"
        if is_numeric:
            summary += f"  • Count: {stats['count']:,}\n"
            summary += f"  • Mean: {stats['mean']:.4f}\n"
            summary += f"  • Std: {stats['std']:.4f}\n"
            summary += f"  • Min: {stats['min']:.4f}\n"
            summary += f"  • Q1: {stats['q1']:.4f}\n"
            summary += f"  • Median: {stats['median']:.4f}\n"
            summary += f"  • Q3: {stats['q3']:.4f}\n"
            summary += f"  • Max: {stats['max']:.4f}\n"
            summary += f"  • Skewness: {stats['skewness']:.4f}\n"
            summary += f"  • Kurtosis: {stats['kurtosis']:.4f}\n"

            # Interpretation
            summary += "\nInterpretation:\n"
            if abs(stats["skewness"]) < 0.5:
                summary += "  • Distribution is approximately symmetric\n"
            elif stats["skewness"] > 0.5:
                summary += "  • Distribution is right-skewed (positive skew)\n"
            else:
                summary += "  • Distribution is left-skewed (negative skew)\n"

            if stats["kurtosis"] < 0:
                summary += "  • Distribution has light tails (platykurtic)\n"
            elif stats["kurtosis"] > 0:
                summary += "  • Distribution has heavy tails (leptokurtic)\n"

        else:
            summary += f"  • Count: {stats['count']:,}\n"
            summary += f"  • Unique Values: {stats['unique']}\n"
            summary += f"  • Most Frequent: {stats['top_value']} ({stats['top_percentage']:.1f}%)\n"

        summary += f"\n🖼️ Plot URL: {plot_url}\n"

        result_data = {
            "column": column,
            "plot_type": plot_type,
            "is_numeric": is_numeric,
            "statistics": stats,
            "plot_url": plot_url,
            "plot_object_key": object_key,
        }

        return ToolResponse(
            payload=result_data,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "column": column,
                "plot_type": plot_type,
            },
            storage_hint="session",
            suggested_name=f"distribution_{column}",
        )

    except Exception as e:
        logger.exception(f"Error plotting distribution: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error plotting distribution: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

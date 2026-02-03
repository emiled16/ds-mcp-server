"""Generate learning curves to visualize model training progress."""

import matplotlib.pyplot as plt
import mlflow
import pandas as pd
from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.utils.plotting import close_figure, save_plot_to_minio


@mcp.tool
@process_tool
@register_tool
async def plot_learning_curves(
    run_id: str,
    metrics: list[str] | None = None,
    smooth: bool = False,
    smoothing_window: int = 10,
) -> str:
    """Generate learning curves showing training metrics over time.

    Creates plots showing how metrics evolved during model training.
    Useful for diagnosing overfitting, underfitting, and convergence.

    Args:
        run_id: MLflow run ID to fetch metrics from
        metrics: List of metric names to plot (plots all if not specified)
        smooth: Apply smoothing to noisy metrics (default: False)
        smoothing_window: Rolling average window size if smooth=True (default: 10)

    Returns:
        ToolResponse with plot URL and metrics data

    Example:
        "Show learning curves for the training run abc123"
        → plot_learning_curves(
            run_id="abc123def456",
            metrics=["train_rmse", "val_rmse"],
            smooth=True
        )
    """
    try:
        # Get MLflow client
        client = mlflow.tracking.MlflowClient()

        # Get run
        try:
            run = client.get_run(run_id)
        except Exception as e:
            logger.exception(f"Error fetching run: {e}")
            return ToolResponse(
                payload=None,
                summary=f"Error: Run '{run_id}' not found",
                metadata={"error": "NotFound", "run_id": run_id},
                storage_hint="never",
            )

        # Get all metrics for this run
        all_metrics = {}
        run_metrics = run.data.metrics

        if not run_metrics:
            return ToolResponse(
                payload=None,
                summary=f"Error: No metrics found for run '{run_id}'",
                metadata={"error": "NoMetrics", "run_id": run_id},
                storage_hint="never",
            )

        # Fetch metric history
        if metrics is None:
            # Fetch all metrics
            metrics_to_plot = list(run_metrics.keys())
        else:
            # Validate requested metrics exist
            missing_metrics = [m for m in metrics if m not in run_metrics]
            if missing_metrics:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Metrics not found: {missing_metrics}. Available: {list(run_metrics.keys())}",
                    metadata={"error": "MetricsNotFound", "missing_metrics": missing_metrics},
                    storage_hint="never",
                )
            metrics_to_plot = metrics

        # Fetch history for each metric
        for metric_name in metrics_to_plot:
            metric_history = client.get_metric_history(run_id, metric_name)
            if metric_history:
                all_metrics[metric_name] = [
                    {"step": m.step, "timestamp": m.timestamp, "value": m.value} for m in metric_history
                ]

        if not all_metrics:
            return ToolResponse(
                payload=None,
                summary=f"Error: No metric history found for run '{run_id}'",
                metadata={"error": "NoHistory", "run_id": run_id},
                storage_hint="never",
            )

        # Determine plot layout
        n_metrics = len(all_metrics)
        if n_metrics == 1:
            fig, axes = plt.subplots(1, 1, figsize=(10, 6))
            axes = [axes]
        elif n_metrics == 2:
            fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        elif n_metrics <= 4:
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            axes = axes.flatten()
        else:
            # More than 4 metrics, use grid
            n_cols = 3
            n_rows = (n_metrics + n_cols - 1) // n_cols
            fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, 5 * n_rows))
            axes = axes.flatten()

        # Plot each metric
        for idx, (metric_name, history) in enumerate(all_metrics.items()):
            ax = axes[idx]

            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(history)

            if smooth and len(df) > smoothing_window:
                # Apply rolling average
                df["value_smooth"] = df["value"].rolling(window=smoothing_window, center=True).mean()
                ax.plot(df["step"], df["value"], alpha=0.3, label="Original", color="gray")
                ax.plot(df["step"], df["value_smooth"], label="Smoothed", linewidth=2)
            else:
                ax.plot(df["step"], df["value"], linewidth=2)

            ax.set_xlabel("Step")
            ax.set_ylabel("Value")
            ax.set_title(metric_name)
            ax.grid(alpha=0.3)

            if smooth and len(df) > smoothing_window:
                ax.legend()

        # Hide unused subplots
        for idx in range(n_metrics, len(axes)):
            axes[idx].set_visible(False)

        fig.suptitle(f"Learning Curves - Run {run_id[:8]}", fontsize=14)
        plt.tight_layout()

        # Save plot
        object_key, plot_url = await save_plot_to_minio(fig, f"learning_curves_{run_id[:8]}")
        close_figure(fig)

        # Generate summary
        summary = "📈 Learning Curves\n\n"
        summary += f"Run ID: {run_id}\n"
        summary += f"Experiment: {run.info.experiment_id}\n"
        summary += f"Metrics Plotted: {len(all_metrics)}\n\n"

        summary += "Metrics:\n"
        for metric_name, history in all_metrics.items():
            values = [h["value"] for h in history]
            summary += f"  • {metric_name}:\n"
            summary += f"    - Steps: {len(history)}\n"
            summary += f"    - Initial: {values[0]:.4f}\n"
            summary += f"    - Final: {values[-1]:.4f}\n"

            # Check for improvement
            if len(values) > 1:
                change = values[-1] - values[0]
                change_pct = (change / abs(values[0])) * 100 if values[0] != 0 else 0
                trend = "↓" if change < 0 else "↑"
                summary += f"    - Change: {trend} {abs(change):.4f} ({abs(change_pct):.1f}%)\n"

        summary += f"\n🖼️ Plot URL: {plot_url}\n"

        result_data = {
            "run_id": run_id,
            "experiment_id": run.info.experiment_id,
            "metrics": all_metrics,
            "plot_url": plot_url,
            "plot_object_key": object_key,
            "smooth": smooth,
            "smoothing_window": smoothing_window if smooth else None,
        }

        return ToolResponse(
            payload=result_data,
            summary=summary,
            metadata={
                "run_id": run_id,
                "n_metrics": len(all_metrics),
                "smooth": smooth,
            },
            storage_hint="session",
            suggested_name=f"learning_curves_{run_id[:8]}",
        )

    except Exception as e:
        logger.exception(f"Error plotting learning curves: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error plotting learning curves: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

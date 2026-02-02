"""Compare metrics and parameters across multiple MLflow runs."""

import os

import mlflow
import pandas as pd
from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_SERVER_URL", os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))


@mcp.tool
@process_tool
@register_tool
async def compare_runs(
    run_ids: list[str],
    metrics_to_compare: list[str] | None = None,
    params_to_compare: list[str] | None = None,
) -> str:
    """Compare metrics and parameters across multiple MLflow runs.

    Creates a comparison table showing selected metrics and parameters
    for the specified runs side-by-side.

    Args:
        run_ids: List of run IDs to compare
        metrics_to_compare: List of metric names to compare (optional, defaults to all)
        params_to_compare: List of parameter names to compare (optional, defaults to all)

    Returns:
        ToolResponse with comparison DataFrame

    Example:
        "Compare these two runs"
        → compare_runs(run_ids=["abc123", "def456"])

        "Compare RMSE and MAE metrics for these runs"
        → compare_runs(
            run_ids=["abc123", "def456", "ghi789"],
            metrics_to_compare=["test_rmse", "test_mae"]
        )
    """
    try:
        if not run_ids or len(run_ids) < 2:
            return ToolResponse(
                payload=None,
                summary="Error: Please provide at least 2 run IDs to compare",
                metadata={"error": "ValidationError"},
                storage_hint="never",
            )

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = mlflow.tracking.MlflowClient()

        # Fetch all runs
        runs = []
        for run_id in run_ids:
            try:
                run = client.get_run(run_id)
                runs.append(run)
            except Exception as e:
                logger.warning(f"Could not fetch run {run_id}: {e}")
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Could not fetch run '{run_id}': {e}",
                    metadata={"error": "NotFound", "run_id": run_id},
                    storage_hint="never",
                )

        # Build comparison table
        comparison_data = []

        for run in runs:
            row = {
                "run_id": run.info.run_id,
                "run_name": run.info.run_name or run.info.run_id[:8],
                "status": run.info.status,
                "start_time": run.info.start_time,
            }

            # Add metrics
            if metrics_to_compare:
                for metric in metrics_to_compare:
                    row[f"metric_{metric}"] = run.data.metrics.get(metric)
            else:
                # Add all metrics
                for metric, value in run.data.metrics.items():
                    row[f"metric_{metric}"] = value

            # Add parameters
            if params_to_compare:
                for param in params_to_compare:
                    row[f"param_{param}"] = run.data.params.get(param)
            else:
                # Add all params
                for param, value in run.data.params.items():
                    row[f"param_{param}"] = value

            comparison_data.append(row)

        # Create DataFrame
        comparison_df = pd.DataFrame(comparison_data)

        # Generate summary
        summary = f"📊 Comparison of {len(runs)} run(s):\n\n"

        # Show run names
        summary += "Runs:\n"
        for i, run in enumerate(runs, 1):
            summary += f"  {i}. {run.info.run_name or run.info.run_id[:8]} ({run.info.run_id})\n"
        summary += "\n"

        # Show metric comparison
        metric_cols = [col for col in comparison_df.columns if col.startswith("metric_")]
        if metric_cols:
            summary += "Metrics Comparison:\n"
            for col in metric_cols[:10]:  # Show first 10
                metric_name = col.replace("metric_", "")
                values = comparison_df[col]

                # Find best value (lowest for most metrics)
                best_idx = values.idxmin() if pd.api.types.is_numeric_dtype(values) else None

                summary += f"  • {metric_name}:\n"
                for idx, value in enumerate(values):
                    marker = "🏆 " if idx == best_idx else "   "
                    run_name = comparison_df.iloc[idx]["run_name"]
                    if pd.notna(value):
                        summary += f"    {marker}{run_name}: {value:.4f}\n"
                    else:
                        summary += f"    {marker}{run_name}: N/A\n"

            if len(metric_cols) > 10:
                summary += f"  ... and {len(metric_cols) - 10} more metrics\n"

        # Show parameter comparison
        param_cols = [col for col in comparison_df.columns if col.startswith("param_")]
        if param_cols:
            summary += "\nParameters Comparison:\n"
            for col in param_cols[:10]:  # Show first 10
                param_name = col.replace("param_", "")
                values = comparison_df[col].unique()

                if len(values) == 1:
                    summary += f"  • {param_name}: {values[0]} (same across all runs)\n"
                else:
                    summary += f"  • {param_name}:\n"
                    for idx, value in enumerate(comparison_df[col]):
                        run_name = comparison_df.iloc[idx]["run_name"]
                        summary += f"    - {run_name}: {value}\n"

            if len(param_cols) > 10:
                summary += f"  ... and {len(param_cols) - 10} more parameters\n"

        return ToolResponse(
            payload=comparison_df,
            summary=summary,
            metadata={
                "num_runs": len(runs),
                "run_ids": run_ids,
                "num_metrics": len(metric_cols),
                "num_params": len(param_cols),
            },
            storage_hint="session",
            suggested_name="run_comparison",
        )

    except Exception as e:
        logger.exception(f"Error comparing runs: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error comparing runs: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

"""List MLflow runs with filtering."""

import os

import mlflow
from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_SERVER_URL", os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))


@mcp.tool
@process_tool
@register_tool
async def list_runs(
    experiment_id: str | None = None,
    experiment_name: str | None = None,
    filter_string: str | None = None,
    max_results: int = 100,
    order_by: list[str] | None = None,
) -> str:
    """List MLflow runs with optional filtering.

    Returns runs from specified experiments with optional filtering by metrics,
    parameters, tags, and attributes.

    Args:
        experiment_id: Filter by experiment ID (optional)
        experiment_name: Filter by experiment name (optional, overrides experiment_id)
        filter_string: MLflow filter string (e.g., "metrics.rmse < 0.5 and params.model = 'xgboost'")
        max_results: Maximum number of runs to return (default: 100)
        order_by: List of order clauses (e.g., ["metrics.rmse ASC", "start_time DESC"])

    Returns:
        ToolResponse with list of runs

    Example:
        "Show me the latest 20 runs"
        → list_runs(max_results=20)

        "Show runs from the mcp-ds-agent experiment"
        → list_runs(experiment_name="mcp-ds-agent")

        "Find runs where RMSE is less than 0.5"
        → list_runs(filter_string="metrics.test_rmse < 0.5", order_by=["metrics.test_rmse ASC"])
    """
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = mlflow.tracking.MlflowClient()

        # Determine experiment IDs
        experiment_ids = []

        if experiment_name:
            # Search for experiment by name
            experiment = client.get_experiment_by_name(experiment_name)
            if experiment:
                experiment_ids = [experiment.experiment_id]
            else:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Experiment '{experiment_name}' not found",
                    metadata={"error": "NotFound", "experiment_name": experiment_name},
                    storage_hint="never",
                )
        elif experiment_id:
            experiment_ids = [experiment_id]
        else:
            # Get all active experiments
            experiments = client.search_experiments(view_type="ACTIVE_ONLY")
            experiment_ids = [exp.experiment_id for exp in experiments]

        # Search runs
        runs = client.search_runs(
            experiment_ids=experiment_ids,
            filter_string=filter_string or "",
            max_results=max_results,
            order_by=order_by or ["start_time DESC"],
        )

        if not runs:
            summary = "No runs found"
            if experiment_name:
                summary += f" in experiment '{experiment_name}'"
            if filter_string:
                summary += f" matching filter: {filter_string}"

            return ToolResponse(
                payload=[],
                summary=summary,
                metadata={"count": 0, "filter_string": filter_string},
                storage_hint="never",
            )

        # Build run data
        runs_data = []
        for run in runs:
            run_data = {
                "run_id": run.info.run_id,
                "run_name": run.info.run_name,
                "experiment_id": run.info.experiment_id,
                "status": run.info.status,
                "start_time": run.info.start_time,
                "end_time": run.info.end_time,
                "artifact_uri": run.info.artifact_uri,
                "lifecycle_stage": run.info.lifecycle_stage,
                "metrics": run.data.metrics,
                "params": run.data.params,
                "tags": run.data.tags,
            }
            runs_data.append(run_data)

        # Generate summary
        summary = f"Found {len(runs_data)} run(s):\n\n"

        for i, run in enumerate(runs_data[:10], 1):  # Show first 10
            summary += f"{i}. {run['run_name'] or run['run_id'][:8]}\n"
            summary += f"   Run ID: {run['run_id']}\n"
            summary += f"   Status: {run['status']}\n"

            # Show key metrics (first 3)
            if run["metrics"]:
                metrics_str = ", ".join([f"{k}={v:.4f}" for k, v in list(run["metrics"].items())[:3]])
                summary += f"   Metrics: {metrics_str}\n"

            # Show key params (first 3)
            if run["params"]:
                params_str = ", ".join([f"{k}={v}" for k, v in list(run["params"].items())[:3]])
                summary += f"   Params: {params_str}\n"

            summary += "\n"

        if len(runs_data) > 10:
            summary += f"... and {len(runs_data) - 10} more runs\n\n"

        if filter_string:
            summary += f"Filter: {filter_string}\n"
        if experiment_name:
            summary += f"Experiment: {experiment_name}\n"

        return ToolResponse(
            payload=runs_data,
            summary=summary,
            metadata={
                "count": len(runs_data),
                "experiment_ids": experiment_ids,
                "filter_string": filter_string,
                "max_results": max_results,
            },
            storage_hint="session",
            suggested_name="mlflow_runs",
        )

    except Exception as e:
        logger.exception(f"Error listing runs: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error listing MLflow runs: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

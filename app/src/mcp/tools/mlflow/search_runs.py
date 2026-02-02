"""Advanced search for MLflow runs with filters."""

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
async def search_runs(
    filter_string: str,
    experiment_names: list[str] | None = None,
    max_results: int = 50,
    order_by: list[str] | None = None,
) -> str:
    """Search for MLflow runs using advanced filters.

    Search across experiments using MLflow filter syntax to find runs matching
    specific criteria (metrics, parameters, tags, etc.).

    Args:
        filter_string: MLflow filter string using syntax:
            - Metrics: "metrics.rmse < 0.5"
            - Parameters: "params.model = 'xgboost'"
            - Tags: "tags.version = '1.0'"
            - Attributes: "attributes.status = 'FINISHED'"
            - Combinations: "metrics.rmse < 0.5 AND params.model = 'xgboost'"
        experiment_names: List of experiment names to search in (optional, searches all if not specified)
        max_results: Maximum number of results (default: 50)
        order_by: List of order clauses (e.g., ["metrics.rmse ASC"])

    Returns:
        ToolResponse with matching runs

    Example:
        "Find runs where test RMSE is less than 0.5"
        → search_runs(filter_string="metrics.test_rmse < 0.5")

        "Find XGBoost runs with RMSE < 0.6, ordered by RMSE"
        → search_runs(
            filter_string="metrics.test_rmse < 0.6 AND params.model_type = 'xgboost'",
            order_by=["metrics.test_rmse ASC"]
        )

        "Find completed runs in the training experiment"
        → search_runs(
            filter_string="attributes.status = 'FINISHED'",
            experiment_names=["mcp-ds-agent"]
        )
    """
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = mlflow.tracking.MlflowClient()

        # Determine experiment IDs
        experiment_ids = []

        if experiment_names:
            for exp_name in experiment_names:
                experiment = client.get_experiment_by_name(exp_name)
                if experiment:
                    experiment_ids.append(experiment.experiment_id)
                else:
                    logger.warning(f"Experiment '{exp_name}' not found, skipping")

            if not experiment_ids:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: None of the specified experiments found: {experiment_names}",
                    metadata={"error": "NotFound", "experiment_names": experiment_names},
                    storage_hint="never",
                )
        else:
            # Search all active experiments
            experiments = client.search_experiments(view_type="ACTIVE_ONLY")
            experiment_ids = [exp.experiment_id for exp in experiments]

        # Search runs
        logger.info(f"Searching runs with filter: {filter_string}")

        try:
            runs = client.search_runs(
                experiment_ids=experiment_ids,
                filter_string=filter_string,
                max_results=max_results,
                order_by=order_by or ["start_time DESC"],
            )
        except Exception as e:
            logger.exception(f"Error in search_runs: {e}")
            return ToolResponse(
                payload=None,
                summary=f"Error executing search: {e}\n\nCheck your filter syntax. Valid examples:\n"
                "  - metrics.rmse < 0.5\n"
                '  - params.model = "xgboost"\n'
                '  - metrics.rmse < 0.5 AND params.model = "xgboost"',
                metadata={"error": "SearchError", "filter_string": filter_string, "details": str(e)},
                storage_hint="never",
            )

        if not runs:
            summary = f"No runs found matching filter:\n{filter_string}"
            if experiment_names:
                summary += f"\n\nSearched in experiments: {', '.join(experiment_names)}"

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
                "metrics": run.data.metrics,
                "params": run.data.params,
                "tags": run.data.tags,
            }
            runs_data.append(run_data)

        # Generate summary
        summary = f"🔍 Found {len(runs_data)} matching run(s):\n\n"
        summary += f"Filter: {filter_string}\n\n"

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

        if experiment_names:
            summary += f"Searched in experiments: {', '.join(experiment_names)}\n"
        else:
            summary += f"Searched in all active experiments ({len(experiment_ids)} total)\n"

        summary += f"Max results: {max_results}"

        return ToolResponse(
            payload=runs_data,
            summary=summary,
            metadata={
                "count": len(runs_data),
                "filter_string": filter_string,
                "experiment_names": experiment_names,
                "max_results": max_results,
            },
            storage_hint="session",
            suggested_name="search_results",
        )

    except Exception as e:
        logger.exception(f"Error searching runs: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error searching runs: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

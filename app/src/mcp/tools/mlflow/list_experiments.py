"""List all MLflow experiments."""

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
async def list_experiments(
    view_type: str = "ACTIVE_ONLY",
) -> str:
    """List all MLflow experiments.

    Returns a list of experiments with their metadata, including experiment name,
    ID, artifact location, and lifecycle stage.

    Args:
        view_type: Type of experiments to view (default: "ACTIVE_ONLY"):
            - "ACTIVE_ONLY" - Only active experiments
            - "DELETED_ONLY" - Only deleted experiments
            - "ALL" - All experiments

    Returns:
        ToolResponse with list of experiments

    Example:
        "Show me all MLflow experiments"
        → list_experiments()

        "Show all experiments including deleted ones"
        → list_experiments(view_type="ALL")
    """
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = mlflow.tracking.MlflowClient()

        # Validate view_type
        valid_types = ["ACTIVE_ONLY", "DELETED_ONLY", "ALL"]
        if view_type not in valid_types:
            return ToolResponse(
                payload=None,
                summary=f"Error: Invalid view_type '{view_type}'. Valid options: {valid_types}",
                metadata={"error": "ValidationError", "valid_types": valid_types},
                storage_hint="never",
            )

        # Get experiments
        experiments = client.search_experiments(view_type=view_type)

        if not experiments:
            summary = f"No experiments found (view_type: {view_type})"
            return ToolResponse(
                payload=[],
                summary=summary,
                metadata={"count": 0, "view_type": view_type},
                storage_hint="never",
            )

        # Build experiment data
        experiments_data = []
        for exp in experiments:
            exp_data = {
                "experiment_id": exp.experiment_id,
                "name": exp.name,
                "artifact_location": exp.artifact_location,
                "lifecycle_stage": exp.lifecycle_stage,
                "tags": dict(exp.tags) if exp.tags else {},
                "creation_time": exp.creation_time,
                "last_update_time": exp.last_update_time,
            }
            experiments_data.append(exp_data)

        # Sort by creation time (newest first)
        experiments_data.sort(key=lambda x: x.get("creation_time", 0), reverse=True)

        # Generate summary
        summary = f"Found {len(experiments_data)} experiment(s):\n\n"

        for exp in experiments_data:
            summary += f"🔬 {exp['name']}\n"
            summary += f"   ID: {exp['experiment_id']}\n"
            summary += f"   Lifecycle: {exp['lifecycle_stage']}\n"

            if exp.get("tags"):
                summary += f"   Tags: {len(exp['tags'])}\n"

            summary += "\n"

        summary += f"View Type: {view_type}\n"
        summary += f"MLflow URI: {MLFLOW_TRACKING_URI}"

        return ToolResponse(
            payload=experiments_data,
            summary=summary,
            metadata={
                "count": len(experiments_data),
                "view_type": view_type,
                "mlflow_uri": MLFLOW_TRACKING_URI,
            },
            storage_hint="session",
            suggested_name="mlflow_experiments",
        )

    except Exception as e:
        logger.exception(f"Error listing experiments: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error listing MLflow experiments: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

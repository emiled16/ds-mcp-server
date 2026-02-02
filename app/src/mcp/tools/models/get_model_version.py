"""Get details about a specific model version from MLflow Model Registry."""

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
async def get_model_version(
    model_name: str,
    version: int | None = None,
) -> str:
    """Get details about a specific model version or all versions of a model.

    Args:
        model_name: Name of the registered model
        version: Specific version number (optional). If not provided, returns all versions.

    Returns:
        ToolResponse with model version details

    Example:
        "Get details for version 2 of temperature_predictor"
        → get_model_version(model_name="temperature_predictor", version=2)

        "Show all versions of my_model"
        → get_model_version(model_name="my_model")
    """
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = mlflow.tracking.MlflowClient()

        # Check if model exists
        try:
            registered_model = client.get_registered_model(model_name)
        except Exception:
            return ToolResponse(
                payload=None,
                summary=f"Error: Registered model '{model_name}' not found",
                metadata={"error": "NotFound", "model_name": model_name},
                storage_hint="never",
            )

        if version is not None:
            # Get specific version
            try:
                model_version = client.get_model_version(model_name, version)
            except Exception:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Version {version} of model '{model_name}' not found",
                    metadata={"error": "NotFound", "model_name": model_name, "version": version},
                    storage_hint="never",
                )

            # Get metrics and params from the run
            run = client.get_run(model_version.run_id)

            version_data = {
                "name": model_version.name,
                "version": model_version.version,
                "creation_timestamp": model_version.creation_timestamp,
                "last_updated_timestamp": model_version.last_updated_timestamp,
                "description": model_version.description,
                "current_stage": model_version.current_stage,
                "status": model_version.status,
                "run_id": model_version.run_id,
                "source": model_version.source,
                "tags": dict(model_version.tags) if model_version.tags else {},
                "run_metrics": run.data.metrics,
                "run_params": run.data.params,
            }

            summary = "Model Version Details:\n\n"
            summary += f"Model: {model_version.name}\n"
            summary += f"Version: {model_version.version}\n"
            summary += f"Stage: {model_version.current_stage}\n"
            summary += f"Status: {model_version.status}\n"
            summary += f"Run ID: {model_version.run_id}\n"

            if model_version.description:
                summary += f"Description: {model_version.description}\n"

            if run.data.metrics:
                summary += "\nMetrics:\n"
                for metric, value in sorted(run.data.metrics.items()):
                    summary += f"  • {metric}: {value:.4f}\n"

            if run.data.params:
                summary += "\nParameters:\n"
                for param, value in sorted(run.data.params.items()):
                    summary += f"  • {param}: {value}\n"

            return ToolResponse(
                payload=version_data,
                summary=summary,
                metadata={
                    "model_name": model_name,
                    "version": version,
                    "stage": model_version.current_stage,
                },
                storage_hint="session",
                suggested_name=f"{model_name}_v{version}_details",
            )

        # Get all versions
        all_versions = client.search_model_versions(f"name='{model_name}'")

        versions_data = []
        for mv in all_versions:
            versions_data.append(
                {
                    "version": mv.version,
                    "current_stage": mv.current_stage,
                    "status": mv.status,
                    "run_id": mv.run_id,
                    "creation_timestamp": mv.creation_timestamp,
                }
            )

        # Sort by version descending
        versions_data.sort(key=lambda x: int(x["version"]), reverse=True)

        summary = f"All Versions of '{model_name}':\n\n"
        summary += f"Total Versions: {len(versions_data)}\n\n"

        for v in versions_data:
            summary += f"Version {v['version']}:\n"
            summary += f"  • Stage: {v['current_stage']}\n"
            summary += f"  • Status: {v['status']}\n"
            summary += f"  • Run ID: {v['run_id']}\n\n"

        summary += f"To get detailed info, use: get_model_version(model_name='{model_name}', version=<number>)"

        return ToolResponse(
            payload={
                "model_name": model_name,
                "description": registered_model.description,
                "versions": versions_data,
            },
            summary=summary,
            metadata={
                "model_name": model_name,
                "total_versions": len(versions_data),
            },
            storage_hint="session",
            suggested_name=f"{model_name}_all_versions",
        )

    except Exception as e:
        logger.exception(f"Error getting model version: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error getting model version: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

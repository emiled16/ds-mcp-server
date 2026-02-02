"""List registered models from MLflow Model Registry."""

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
async def list_registered_models(
    name_filter: str | None = None,
) -> str:
    """List all registered models in MLflow Model Registry.

    Args:
        name_filter: Optional filter to search for models by name (case-insensitive substring match)

    Returns:
        ToolResponse with list of registered models and their versions

    Example:
        "Show me all registered models"
        → list_registered_models()

        "List models with 'xgboost' in the name"
        → list_registered_models(name_filter="xgboost")
    """
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = mlflow.tracking.MlflowClient()

        # Get all registered models
        registered_models = client.search_registered_models()

        # Filter if name_filter provided
        if name_filter:
            name_filter_lower = name_filter.lower()
            registered_models = [rm for rm in registered_models if name_filter_lower in rm.name.lower()]

        if not registered_models:
            summary = "No registered models found."
            if name_filter:
                summary += f" (filter: '{name_filter}')"

            return ToolResponse(
                payload=[],
                summary=summary,
                metadata={"count": 0, "filter": name_filter},
                storage_hint="never",
            )

        # Build detailed model list
        models_data = []
        for rm in registered_models:
            # Get latest versions per stage
            versions_by_stage = {}
            for version in rm.latest_versions:
                versions_by_stage[version.current_stage] = {
                    "version": version.version,
                    "run_id": version.run_id,
                    "status": version.status,
                }

            model_info = {
                "name": rm.name,
                "creation_timestamp": rm.creation_timestamp,
                "last_updated_timestamp": rm.last_updated_timestamp,
                "description": rm.description,
                "tags": dict(rm.tags) if rm.tags else {},
                "versions_by_stage": versions_by_stage,
                "total_versions": len(client.search_model_versions(f"name='{rm.name}'")),
            }
            models_data.append(model_info)

        # Create summary
        summary = f"Found {len(models_data)} registered model(s):\n\n"

        for model in models_data:
            summary += f"📦 {model['name']}\n"
            if model.get("description"):
                summary += f"   Description: {model['description']}\n"
            summary += f"   Total Versions: {model['total_versions']}\n"

            if model["versions_by_stage"]:
                summary += "   Latest Versions:\n"
                for stage, version_info in model["versions_by_stage"].items():
                    summary += f"      • {stage}: v{version_info['version']} (status: {version_info['status']})\n"
            else:
                summary += "   No versions in staging/production\n"

            summary += "\n"

        summary += "\nTo promote a model version, use: promote_model_stage(model_name=..., version=..., stage=...)"

        return ToolResponse(
            payload=models_data,
            summary=summary,
            metadata={
                "count": len(models_data),
                "filter": name_filter,
                "mlflow_uri": MLFLOW_TRACKING_URI,
            },
            storage_hint="session",
            suggested_name="registered_models_list",
        )

    except Exception as e:
        logger.exception(f"Error listing registered models: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error listing registered models: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

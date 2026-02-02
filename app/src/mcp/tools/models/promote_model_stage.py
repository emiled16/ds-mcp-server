"""Promote model version to a different stage in MLflow Model Registry."""

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
async def promote_model_stage(
    model_name: str,
    version: int,
    stage: str,
    archive_existing: bool = True,
) -> str:
    """Promote a model version to a specific stage in MLflow Model Registry.

    Args:
        model_name: Name of the registered model
        version: Version number to promote
        stage: Target stage ("Staging", "Production", "Archived", or "None")
        archive_existing: If True, archive existing versions in the target stage (default: True)

    Returns:
        ToolResponse with promotion details

    Example:
        "Promote model 'temperature_predictor' version 2 to production"
        → promote_model_stage(model_name="temperature_predictor", version=2, stage="Production")

        "Move version 1 to staging"
        → promote_model_stage(model_name="my_model", version=1, stage="Staging")
    """
    # Validate stage
    valid_stages = ["Staging", "Production", "Archived", "None"]
    if stage not in valid_stages:
        return ToolResponse(
            payload=None,
            summary=f"Error: Invalid stage '{stage}'. Must be one of: {valid_stages}",
            metadata={"error": "ValidationError", "valid_stages": valid_stages},
            storage_hint="never",
        )

    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = mlflow.tracking.MlflowClient()

        # Check if model exists
        try:
            client.get_registered_model(model_name)
        except Exception:
            return ToolResponse(
                payload=None,
                summary=f"Error: Registered model '{model_name}' not found",
                metadata={"error": "NotFound", "model_name": model_name},
                storage_hint="never",
            )

        # Check if version exists
        try:
            model_version = client.get_model_version(model_name, version)
        except Exception:
            return ToolResponse(
                payload=None,
                summary=f"Error: Version {version} of model '{model_name}' not found",
                metadata={"error": "NotFound", "model_name": model_name, "version": version},
                storage_hint="never",
            )

        # Archive existing versions in target stage if requested
        archived_versions = []
        if archive_existing and stage in ["Staging", "Production"]:
            existing_versions = client.get_latest_versions(model_name, stages=[stage])
            for existing_version in existing_versions:
                if existing_version.version != str(version):
                    client.transition_model_version_stage(
                        name=model_name,
                        version=existing_version.version,
                        stage="Archived",
                    )
                    archived_versions.append(existing_version.version)
                    logger.info(f"Archived version {existing_version.version} from {stage}")

        # Promote the target version
        updated_version = client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage=stage,
        )

        summary = "✅ Successfully promoted model version!\n\n"
        summary += f"Model: {model_name}\n"
        summary += f"Version: {version}\n"
        summary += f"New Stage: {stage}\n"
        summary += f"Run ID: {updated_version.run_id}\n"

        if archived_versions:
            summary += f"\nArchived versions: {', '.join(map(str, archived_versions))}"

        summary += f"\n\nTo view all versions, use: get_model_version(model_name='{model_name}')"

        return ToolResponse(
            payload={
                "model_name": model_name,
                "version": version,
                "stage": stage,
                "run_id": updated_version.run_id,
                "archived_versions": archived_versions,
            },
            summary=summary,
            metadata={
                "model_name": model_name,
                "version": version,
                "stage": stage,
            },
            storage_hint="session",
            suggested_name=f"promotion_{model_name}_v{version}",
        )

    except Exception as e:
        logger.exception(f"Error promoting model: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error promoting model: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

"""Load model metadata for inspection."""

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
async def load_model_for_inference(
    model_source: dict,
) -> str:
    """Load and inspect a model's metadata without making predictions.

    Loads a model from MLflow and returns information about it (input/output schema,
    metadata, etc.) without actually making predictions. Useful for inspecting model
    details before inference.

    Args:
        model_source: Model identifier:
            - {"run_id": "abc123"}
            - {"model_name": "my_model"}
            - {"model_name": "my_model", "version": 2}
            - {"model_name": "my_model", "stage": "Production"}

    Returns:
        ToolResponse with model metadata

    Example:
        "Load the production model and show me its details"
        → load_model_for_inference(
            model_source={"model_name": "sales_model", "stage": "Production"}
        )
    """
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

        # Determine model URI
        run_id = model_source.get("run_id")
        model_name = model_source.get("model_name")
        version = model_source.get("version")
        stage = model_source.get("stage")

        if run_id:
            model_uri = f"runs:/{run_id}/model"
            model_identifier = f"run:{run_id}"
            model_version_info = None
        elif model_name:
            client = mlflow.tracking.MlflowClient()
            if version:
                model_uri = f"models:/{model_name}/{version}"
                model_identifier = f"{model_name} v{version}"
                try:
                    model_version_info = client.get_model_version(model_name, version)
                except Exception:
                    model_version_info = None
            elif stage:
                model_uri = f"models:/{model_name}/{stage}"
                model_identifier = f"{model_name} ({stage})"
                try:
                    latest_versions = client.get_latest_versions(model_name, stages=[stage])
                    model_version_info = latest_versions[0] if latest_versions else None
                except Exception:
                    model_version_info = None
            else:
                try:
                    latest_versions = client.get_latest_versions(model_name, stages=["None", "Staging", "Production"])
                    if not latest_versions:
                        return ToolResponse(
                            payload=None,
                            summary=f"Error: No versions found for model '{model_name}'",
                            metadata={"error": "NotFound", "model_name": model_name},
                            storage_hint="never",
                        )
                    latest = max(latest_versions, key=lambda v: int(v.version))
                    model_uri = f"models:/{model_name}/{latest.version}"
                    model_identifier = f"{model_name} v{latest.version}"
                    model_version_info = latest
                except Exception as e:
                    return ToolResponse(
                        payload=None,
                        summary=f"Error: Model '{model_name}' not found: {e}",
                        metadata={"error": "NotFound", "model_name": model_name, "details": str(e)},
                        storage_hint="never",
                    )
        else:
            return ToolResponse(
                payload=None,
                summary="Error: model_source must include 'run_id' or 'model_name'",
                metadata={"error": "ValidationError"},
                storage_hint="never",
            )

        # Load model
        logger.info(f"Loading model metadata from: {model_uri}")
        try:
            model = mlflow.pyfunc.load_model(model_uri)
        except Exception as e:
            logger.exception(f"Error loading model: {e}")
            return ToolResponse(
                payload=None,
                summary=f"Error loading model from '{model_uri}': {e}",
                metadata={"error": "ModelLoadError", "model_uri": model_uri, "details": str(e)},
                storage_hint="never",
            )

        # Get model metadata
        metadata = model.metadata.to_dict() if hasattr(model, "metadata") else {}

        # Get run info if available
        run_info = {}
        if run_id:
            try:
                client = mlflow.tracking.MlflowClient()
                run = client.get_run(run_id)
                run_info = {
                    "run_name": run.info.run_name,
                    "experiment_id": run.info.experiment_id,
                    "start_time": run.info.start_time,
                    "end_time": run.info.end_time,
                    "status": run.info.status,
                    "metrics": run.data.metrics,
                    "params": run.data.params,
                }
            except Exception as e:
                logger.warning(f"Could not load run info: {e}")

        # Generate summary
        summary = "📦 Model Loaded Successfully!\n\n"
        summary += f"Model: {model_identifier}\n"
        summary += f"URI: {model_uri}\n\n"

        if model_version_info:
            summary += "Version Info:\n"
            summary += f"  • Version: {model_version_info.version}\n"
            summary += f"  • Stage: {model_version_info.current_stage}\n"
            summary += f"  • Status: {model_version_info.status}\n"
            summary += f"  • Run ID: {model_version_info.run_id}\n\n"

        if metadata:
            summary += "Model Metadata:\n"
            for key, value in list(metadata.items())[:10]:
                summary += f"  • {key}: {value}\n"

        if run_info:
            summary += "\nRun Info:\n"
            if run_info.get("run_name"):
                summary += f"  • Run Name: {run_info['run_name']}\n"
            if run_info.get("status"):
                summary += f"  • Status: {run_info['status']}\n"
            if run_info.get("metrics"):
                summary += f"  • Metrics: {len(run_info['metrics'])} logged\n"
                # Show top metrics
                for metric, value in list(run_info["metrics"].items())[:5]:
                    summary += f"    - {metric}: {value:.4f}\n"
            if run_info.get("params"):
                summary += f"  • Parameters: {len(run_info['params'])} logged\n"

        summary += (
            "\n💡 Use predict(), batch_predict(), or predict_with_pipeline() to make predictions with this model."
        )

        result_data = {
            "model_uri": model_uri,
            "model_identifier": model_identifier,
            "metadata": metadata,
            "run_info": run_info,
        }

        if model_version_info:
            result_data["version_info"] = {
                "version": model_version_info.version,
                "stage": model_version_info.current_stage,
                "status": model_version_info.status,
                "run_id": model_version_info.run_id,
            }

        return ToolResponse(
            payload=result_data,
            summary=summary,
            metadata={
                "model_source": model_source,
                "model_uri": model_uri,
            },
            storage_hint="session",
            suggested_name=f"model_{model_identifier.replace(':', '_').replace('/', '_')}",
        )

    except Exception as e:
        logger.exception(f"Error loading model: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error loading model: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

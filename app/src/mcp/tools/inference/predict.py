"""Make predictions with a trained model."""

import os

import mlflow
import pandas as pd
from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_SERVER_URL", os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))


@mcp.tool
@process_tool
@register_tool
async def predict(
    dataset_id: str,
    model_source: dict,
    return_probabilities: bool = False,
) -> str:
    """Make predictions using a trained model.

    Loads a model from MLflow and applies it to a dataset to generate predictions.
    Supports loading models by run_id, registered model name, or model version.

    Args:
        dataset_id: Entity ID of the dataset to predict on
        model_source: Model identifier, one of:
            - {"run_id": "abc123"} - Load from specific MLflow run
            - {"model_name": "my_model"} - Load latest version of registered model
            - {"model_name": "my_model", "version": 2} - Load specific version
            - {"model_name": "my_model", "stage": "Production"} - Load by stage
        return_probabilities: For classification, return prediction probabilities (default: False)

    Returns:
        ToolResponse with predictions as a new dataset

    Example:
        "Make predictions on the test data using the trained model"
        → predict(
            dataset_id="test_data_123",
            model_source={"run_id": "abc123"}
        )

        "Use the production model to predict"
        → predict(
            dataset_id="new_data_456",
            model_source={"model_name": "sales_predictor", "stage": "Production"}
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

        # Determine model URI
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

        run_id = model_source.get("run_id")
        model_name = model_source.get("model_name")
        version = model_source.get("version")
        stage = model_source.get("stage")

        if run_id:
            model_uri = f"runs:/{run_id}/model"
            model_identifier = f"run:{run_id}"
        elif model_name:
            if version:
                model_uri = f"models:/{model_name}/{version}"
                model_identifier = f"{model_name} v{version}"
            elif stage:
                model_uri = f"models:/{model_name}/{stage}"
                model_identifier = f"{model_name} ({stage})"
            else:
                # Get latest version
                client = mlflow.tracking.MlflowClient()
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
        logger.info(f"Loading model from: {model_uri}")
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

        # Make predictions
        original_shape = df.shape
        logger.info(f"Making predictions on {original_shape[0]:,} rows")

        try:
            predictions = model.predict(df)

            # Handle different prediction output formats
            if isinstance(predictions, pd.DataFrame):
                result_df = df.copy()
                # Merge predictions
                for col in predictions.columns:
                    result_df[col] = predictions[col]
            elif isinstance(predictions, pd.Series):
                result_df = df.copy()
                result_df["prediction"] = predictions
            else:
                # numpy array or similar
                result_df = df.copy()
                result_df["prediction"] = predictions

        except Exception as e:
            logger.exception(f"Error making predictions: {e}")
            return ToolResponse(
                payload=None,
                summary=f"Error making predictions: {e}",
                metadata={"error": "PredictionError", "details": str(e)},
                storage_hint="never",
            )

        # Generate summary
        prediction_cols = [col for col in result_df.columns if col not in df.columns]

        summary = "✅ Predictions completed successfully!\n\n"
        summary += f"Model: {model_identifier}\n"
        summary += f"Dataset: {original_shape[0]:,} rows × {original_shape[1]} columns\n"
        summary += f"Result: {result_df.shape[0]:,} rows × {result_df.shape[1]} columns\n"

        if prediction_cols:
            summary += f"\nPrediction columns added: {', '.join(prediction_cols)}\n"

        # Show prediction stats
        if "prediction" in result_df.columns:
            pred_series = result_df["prediction"]
            summary += "\nPrediction Statistics:\n"

            # Check if numeric
            if pd.api.types.is_numeric_dtype(pred_series):
                summary += f"  • Mean: {pred_series.mean():.4f}\n"
                summary += f"  • Std: {pred_series.std():.4f}\n"
                summary += f"  • Min: {pred_series.min():.4f}\n"
                summary += f"  • Max: {pred_series.max():.4f}\n"
            else:
                # Categorical
                value_counts = pred_series.value_counts().head(5)
                summary += "  • Top predictions:\n"
                for val, count in value_counts.items():
                    pct = (count / len(pred_series)) * 100
                    summary += f"    - {val}: {count} ({pct:.1f}%)\n"

        # Preview
        preview_cols = list(df.columns[:3]) + prediction_cols
        preview = result_df[preview_cols].head(5).to_string(max_colwidth=30)
        summary += f"\nPreview:\n{preview}"

        return ToolResponse(
            payload=result_df,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "model_source": model_source,
                "model_uri": model_uri,
                "original_shape": original_shape,
                "result_shape": result_df.shape,
                "prediction_columns": prediction_cols,
            },
            storage_hint="session",
            suggested_name=f"{entity.suggested_name or 'data'}_predictions",
        )

    except Exception as e:
        logger.exception(f"Error in predict: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error making predictions: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

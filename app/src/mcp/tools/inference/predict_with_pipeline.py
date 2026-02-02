"""Apply feature pipeline and make predictions in one step."""

import mlflow
import pandas as pd
from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def predict_with_pipeline(
    dataset_id: str,
    pipeline_run_id: str,
    model_source: dict,
) -> str:
    """Apply a feature pipeline and make predictions in one step.

    Loads a feature pipeline from MLflow, applies it to transform the data,
    then loads a model and makes predictions on the transformed data.

    Args:
        dataset_id: Entity ID of the raw dataset
        pipeline_run_id: MLflow run ID of the feature pipeline
        model_source: Model identifier (same format as predict tool):
            - {"run_id": "abc123"}
            - {"model_name": "my_model", "version": 2}
            - {"model_name": "my_model", "stage": "Production"}

    Returns:
        ToolResponse with predictions on the transformed data

    Example:
        "Transform the data and make predictions"
        → predict_with_pipeline(
            dataset_id="raw_data_123",
            pipeline_run_id="pipeline_abc",
            model_source={"model_name": "sales_model", "stage": "Production"}
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

        original_shape = df.shape

        # Step 1: Load and apply feature pipeline
        logger.info(f"Loading feature pipeline from run: {pipeline_run_id}")
        pipeline_uri = f"runs:/{pipeline_run_id}/pipeline"

        try:
            pipeline = mlflow.pyfunc.load_model(pipeline_uri)
        except Exception as e:
            logger.exception(f"Error loading pipeline: {e}")
            return ToolResponse(
                payload=None,
                summary=f"Error loading feature pipeline from '{pipeline_uri}': {e}",
                metadata={"error": "PipelineLoadError", "pipeline_uri": pipeline_uri, "details": str(e)},
                storage_hint="never",
            )

        logger.info("Applying feature pipeline...")
        try:
            transformed_df = pipeline.predict(df)
        except Exception as e:
            logger.exception(f"Error applying pipeline: {e}")
            return ToolResponse(
                payload=None,
                summary=f"Error applying feature pipeline: {e}",
                metadata={"error": "PipelineTransformError", "details": str(e)},
                storage_hint="never",
            )

        transformed_shape = transformed_df.shape
        logger.info(f"Pipeline applied: {original_shape} → {transformed_shape}")

        # Step 2: Load model
        run_id = model_source.get("run_id")
        model_name = model_source.get("model_name")
        version = model_source.get("version")
        stage = model_source.get("stage")

        if run_id:
            model_uri = f"runs:/{run_id}/model"
            model_identifier = f"run:{run_id}"
        elif model_name:
            client = mlflow.tracking.MlflowClient()
            if version:
                model_uri = f"models:/{model_name}/{version}"
                model_identifier = f"{model_name} v{version}"
            elif stage:
                model_uri = f"models:/{model_name}/{stage}"
                model_identifier = f"{model_name} ({stage})"
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

        # Step 3: Make predictions
        logger.info("Making predictions on transformed data...")
        try:
            predictions = model.predict(transformed_df)

            # Handle different prediction formats
            if isinstance(predictions, pd.DataFrame):
                result_df = transformed_df.copy()
                for col in predictions.columns:
                    result_df[col] = predictions[col]
            elif isinstance(predictions, pd.Series):
                result_df = transformed_df.copy()
                result_df["prediction"] = predictions
            else:
                result_df = transformed_df.copy()
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
        prediction_cols = [col for col in result_df.columns if col not in transformed_df.columns]

        summary = "✅ Pipeline + Prediction completed!\n\n"
        summary += f"Pipeline Run: {pipeline_run_id}\n"
        summary += f"Model: {model_identifier}\n\n"
        summary += "Data Flow:\n"
        summary += f"  1. Original: {original_shape[0]:,} rows × {original_shape[1]} columns\n"
        summary += f"  2. Transformed: {transformed_shape[0]:,} rows × {transformed_shape[1]} columns\n"
        summary += f"  3. Predictions: {result_df.shape[0]:,} rows × {result_df.shape[1]} columns\n"

        if prediction_cols:
            summary += f"\nPrediction columns: {', '.join(prediction_cols)}\n"

        # Show prediction stats
        if "prediction" in result_df.columns:
            pred_series = result_df["prediction"]
            summary += "\nPrediction Statistics:\n"

            if pd.api.types.is_numeric_dtype(pred_series):
                summary += f"  • Mean: {pred_series.mean():.4f}\n"
                summary += f"  • Std: {pred_series.std():.4f}\n"
                summary += f"  • Min: {pred_series.min():.4f}\n"
                summary += f"  • Max: {pred_series.max():.4f}\n"
            else:
                value_counts = pred_series.value_counts().head(5)
                summary += "  • Top predictions:\n"
                for val, count in value_counts.items():
                    pct = (count / len(pred_series)) * 100
                    summary += f"    - {val}: {count} ({pct:.1f}%)\n"

        return ToolResponse(
            payload=result_df,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "pipeline_run_id": pipeline_run_id,
                "model_source": model_source,
                "model_uri": model_uri,
                "original_shape": original_shape,
                "transformed_shape": transformed_shape,
                "result_shape": result_df.shape,
            },
            storage_hint="session",
            suggested_name=f"{entity.suggested_name or 'data'}_pipeline_predictions",
        )

    except Exception as e:
        logger.exception(f"Error in predict_with_pipeline: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error in pipeline prediction: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

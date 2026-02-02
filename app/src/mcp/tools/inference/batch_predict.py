"""Batch predictions for large datasets."""

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
async def batch_predict(
    dataset_id: str,
    model_source: dict,
    batch_size: int = 1000,
) -> str:
    """Make batch predictions on large datasets with progress tracking.

    Processes data in batches to handle large datasets efficiently. Useful when
    dataset size exceeds available memory or for monitoring prediction progress.

    Args:
        dataset_id: Entity ID of the dataset to predict on
        model_source: Model identifier (same format as predict tool):
            - {"run_id": "abc123"}
            - {"model_name": "my_model"}
            - {"model_name": "my_model", "version": 2}
            - {"model_name": "my_model", "stage": "Production"}
        batch_size: Number of rows to process per batch (default: 1000)

    Returns:
        ToolResponse with all predictions as a dataset

    Example:
        "Make batch predictions on the large test dataset"
        → batch_predict(
            dataset_id="large_test_123",
            model_source={"model_name": "sales_model", "stage": "Production"},
            batch_size=500
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

        # Determine model URI (same logic as predict tool)
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

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
                # Get latest version
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

        # Process in batches
        total_rows = len(df)
        num_batches = (total_rows + batch_size - 1) // batch_size

        logger.info(f"Processing {total_rows:,} rows in {num_batches} batches of {batch_size}")

        all_predictions = []

        for batch_idx in range(num_batches):
            start_idx = batch_idx * batch_size
            end_idx = min((batch_idx + 1) * batch_size, total_rows)

            batch_df = df.iloc[start_idx:end_idx]

            logger.info(f"Batch {batch_idx + 1}/{num_batches}: rows {start_idx}-{end_idx}")

            try:
                batch_predictions = model.predict(batch_df)

                # Handle different prediction formats
                if isinstance(batch_predictions, pd.DataFrame):
                    all_predictions.append(batch_predictions)
                elif isinstance(batch_predictions, pd.Series):
                    all_predictions.append(pd.DataFrame({"prediction": batch_predictions}))
                else:
                    # numpy array
                    all_predictions.append(pd.DataFrame({"prediction": batch_predictions}))

            except Exception as e:
                logger.exception(f"Error in batch {batch_idx + 1}: {e}")
                return ToolResponse(
                    payload=None,
                    summary=f"Error in batch {batch_idx + 1}/{num_batches}: {e}",
                    metadata={"error": "PredictionError", "batch": batch_idx + 1, "details": str(e)},
                    storage_hint="never",
                )

        # Concatenate all predictions
        all_predictions_df = pd.concat(all_predictions, ignore_index=True)

        # Merge with original data
        result_df = df.copy()
        for col in all_predictions_df.columns:
            result_df[col] = all_predictions_df[col].values

        # Generate summary
        prediction_cols = [col for col in result_df.columns if col not in df.columns]

        summary = "✅ Batch predictions completed!\n\n"
        summary += f"Model: {model_identifier}\n"
        summary += f"Dataset: {total_rows:,} rows × {df.shape[1]} columns\n"
        summary += f"Batches: {num_batches} × {batch_size} rows\n"
        summary += f"Result: {result_df.shape[0]:,} rows × {result_df.shape[1]} columns\n"

        if prediction_cols:
            summary += f"\nPrediction columns added: {', '.join(prediction_cols)}\n"

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
                "model_source": model_source,
                "model_uri": model_uri,
                "batch_size": batch_size,
                "num_batches": num_batches,
                "total_rows": total_rows,
            },
            storage_hint="session",
            suggested_name=f"{entity.suggested_name or 'data'}_batch_predictions",
        )

    except Exception as e:
        logger.exception(f"Error in batch_predict: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error making batch predictions: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

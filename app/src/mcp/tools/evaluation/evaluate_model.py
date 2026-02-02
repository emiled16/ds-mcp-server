"""Evaluate a trained model on new data."""

import mlflow
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def evaluate_model(
    dataset_id: str,
    model_source: dict,
    target_column: str,
    problem_type: str | None = None,
) -> str:
    """Evaluate a trained model on a validation/test dataset.

    Computes comprehensive metrics for regression or classification tasks.
    Automatically detects problem type if not specified.

    Args:
        dataset_id: Entity ID of the dataset with true labels
        model_source: Model identifier:
            - {"run_id": "abc123"}
            - {"model_name": "my_model", "version": 2}
            - {"model_name": "my_model", "stage": "Production"}
        target_column: Name of the column containing true labels
        problem_type: "regression" or "classification" (auto-detected if not specified)

    Returns:
        ToolResponse with evaluation metrics

    Example:
        "Evaluate the production model on the test data"
        → evaluate_model(
            dataset_id="test_data_123",
            model_source={"model_name": "sales_model", "stage": "Production"},
            target_column="sales"
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

        # Check target column exists
        if target_column not in df.columns:
            return ToolResponse(
                payload=None,
                summary=f"Error: Target column '{target_column}' not found in dataset. Available: {list(df.columns)}",
                metadata={"error": "ValidationError", "target_column": target_column},
                storage_hint="never",
            )

        # Get true labels
        y_true = df[target_column]

        # Load model and make predictions
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
                summary=f"Error loading model: {e}",
                metadata={"error": "ModelLoadError", "details": str(e)},
                storage_hint="never",
            )

        # Make predictions
        try:
            predictions = model.predict(df)

            # Extract prediction values
            if isinstance(predictions, pd.DataFrame):
                # Try to find prediction column
                pred_cols = [col for col in predictions.columns if "pred" in col.lower()]
                if pred_cols:
                    y_pred = predictions[pred_cols[0]].values
                else:
                    y_pred = predictions.iloc[:, 0].values
            elif isinstance(predictions, pd.Series):
                y_pred = predictions.values
            else:
                y_pred = np.array(predictions)

        except Exception as e:
            logger.exception(f"Error making predictions: {e}")
            return ToolResponse(
                payload=None,
                summary=f"Error making predictions: {e}",
                metadata={"error": "PredictionError", "details": str(e)},
                storage_hint="never",
            )

        # Auto-detect problem type if not specified
        if not problem_type:
            # Check if target is numeric and has many unique values
            if pd.api.types.is_numeric_dtype(y_true):
                unique_ratio = len(y_true.unique()) / len(y_true)
                if unique_ratio > 0.05:  # More than 5% unique values
                    problem_type = "regression"
                else:
                    problem_type = "classification"
            else:
                problem_type = "classification"

        logger.info(f"Problem type: {problem_type}")

        # Calculate metrics based on problem type
        metrics = {}

        if problem_type == "regression":
            metrics["mse"] = float(mean_squared_error(y_true, y_pred))
            metrics["rmse"] = float(np.sqrt(metrics["mse"]))
            metrics["mae"] = float(mean_absolute_error(y_true, y_pred))
            metrics["r2"] = float(r2_score(y_true, y_pred))

            # Additional regression metrics
            residuals = y_true - y_pred
            metrics["mean_residual"] = float(np.mean(residuals))
            metrics["std_residual"] = float(np.std(residuals))

        else:  # classification
            # Handle multi-class vs binary
            unique_classes = np.unique(y_true)
            n_classes = len(unique_classes)

            metrics["accuracy"] = float(accuracy_score(y_true, y_pred))

            if n_classes == 2:
                # Binary classification
                metrics["precision"] = float(precision_score(y_true, y_pred, zero_division=0))
                metrics["recall"] = float(recall_score(y_true, y_pred, zero_division=0))
                metrics["f1"] = float(f1_score(y_true, y_pred, zero_division=0))
            else:
                # Multi-class classification
                metrics["precision_macro"] = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
                metrics["recall_macro"] = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
                metrics["f1_macro"] = float(f1_score(y_true, y_pred, average="macro", zero_division=0))

            # Confusion matrix
            cm = confusion_matrix(y_true, y_pred)
            metrics["confusion_matrix"] = cm.tolist()

        # Generate summary
        summary = "📊 Model Evaluation Results\n\n"
        summary += f"Model: {model_identifier}\n"
        summary += f"Dataset: {len(df):,} samples\n"
        summary += f"Problem Type: {problem_type.title()}\n\n"

        summary += "Metrics:\n"
        for metric, value in metrics.items():
            if metric != "confusion_matrix":
                if isinstance(value, float):
                    summary += f"  • {metric}: {value:.4f}\n"
                else:
                    summary += f"  • {metric}: {value}\n"

        if "confusion_matrix" in metrics:
            summary += "\nConfusion Matrix:\n"
            cm = np.array(metrics["confusion_matrix"])
            summary += f"{cm}\n"

        result_data = {
            "model_identifier": model_identifier,
            "model_uri": model_uri,
            "problem_type": problem_type,
            "n_samples": len(df),
            "metrics": metrics,
        }

        return ToolResponse(
            payload=result_data,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "model_source": model_source,
                "problem_type": problem_type,
            },
            storage_hint="session",
            suggested_name=f"evaluation_{model_identifier.replace(':', '_').replace('/', '_')}",
        )

    except Exception as e:
        logger.exception(f"Error evaluating model: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error evaluating model: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

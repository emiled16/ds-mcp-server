"""Generate confusion matrix plots for classification models."""

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
import seaborn as sns
from loguru import logger
from sklearn.metrics import confusion_matrix

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry
from src.utils.plotting import close_figure, save_plot_to_minio


@mcp.tool
@process_tool
@register_tool
async def plot_confusion_matrix(
    dataset_id: str,
    model_source: dict,
    target_column: str,
    normalize: str | None = None,
    cmap: str = "Blues",
) -> str:
    """Generate a confusion matrix heatmap for a classification model.

    Creates a visualization showing the model's predictions vs actual labels.
    Useful for understanding classification errors and model behavior.

    Args:
        dataset_id: Entity ID of the dataset with true labels
        model_source: Model identifier:
            - {"run_id": "abc123"}
            - {"model_name": "my_model", "version": 2}
            - {"model_name": "my_model", "stage": "Production"}
        target_column: Name of the column containing true labels
        normalize: Normalization mode - "true", "pred", "all", or None (default: None)
        cmap: Matplotlib colormap name (default: "Blues")

    Returns:
        ToolResponse with plot URL and confusion matrix data

    Example:
        "Show me the confusion matrix for the production classifier"
        → plot_confusion_matrix(
            dataset_id="test_data_123",
            model_source={"model_name": "classifier", "stage": "Production"},
            target_column="label",
            normalize="true"
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

        # Check target column
        if target_column not in df.columns:
            return ToolResponse(
                payload=None,
                summary=f"Error: Target column '{target_column}' not found in dataset. Available: {list(df.columns)}",
                metadata={"error": "ValidationError", "target_column": target_column},
                storage_hint="never",
            )

        y_true = df[target_column]

        # Load model
        run_id = model_source.get("run_id")
        model_name = model_source.get("model_name")
        version = model_source.get("version")
        stage = model_source.get("stage")

        if run_id:
            model_uri = f"runs:/{run_id}/model"
            model_identifier = f"run:{run_id[:8]}"
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
        model = mlflow.pyfunc.load_model(model_uri)

        # Make predictions
        try:
            predictions = model.predict(df)

            # Extract prediction values
            if isinstance(predictions, pd.DataFrame):
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

        # Compute confusion matrix
        cm = confusion_matrix(y_true, y_pred, normalize=normalize)
        labels = sorted(np.unique(np.concatenate([y_true.unique(), np.unique(y_pred)])))

        # Create plot
        fig, ax = plt.subplots(figsize=(max(8, len(labels)), max(6, len(labels) * 0.8)))

        # Use seaborn for better styling
        sns.heatmap(
            cm,
            annot=True,
            fmt=".2f" if normalize else "d",
            cmap=cmap,
            xticklabels=labels,
            yticklabels=labels,
            ax=ax,
            cbar_kws={"label": "Count" if not normalize else "Proportion"},
        )

        ax.set_xlabel("Predicted Label")
        ax.set_ylabel("True Label")

        title = f"Confusion Matrix: {model_identifier}"
        if normalize:
            title += f" (normalized by {normalize})"
        ax.set_title(title)

        plt.tight_layout()

        # Save plot
        object_key, plot_url = await save_plot_to_minio(
            fig, f"confusion_matrix_{model_identifier.replace(':', '_').replace('/', '_')}"
        )
        close_figure(fig)

        # Generate summary
        summary = "📊 Confusion Matrix\n\n"
        summary += f"Model: {model_identifier}\n"
        summary += f"Dataset: {len(df):,} samples\n"
        summary += f"Classes: {len(labels)}\n"

        if normalize:
            summary += f"Normalization: {normalize}\n"

        summary += "\nConfusion Matrix:\n"
        summary += f"{cm}\n"

        # Calculate per-class metrics
        summary += "\nPer-Class Metrics:\n"
        for i, label in enumerate(labels):
            true_positive = cm[i, i]
            false_positive = cm[:, i].sum() - true_positive
            false_negative = cm[i, :].sum() - true_positive

            precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) > 0 else 0
            recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            summary += f"  • Class {label}: Precision={precision:.3f}, Recall={recall:.3f}, F1={f1:.3f}\n"

        summary += f"\n🖼️ Plot URL: {plot_url}\n"

        result_data = {
            "model_identifier": model_identifier,
            "model_uri": model_uri,
            "confusion_matrix": cm.tolist(),
            "labels": [str(label) for label in labels],
            "normalize": normalize,
            "plot_url": plot_url,
            "plot_object_key": object_key,
        }

        return ToolResponse(
            payload=result_data,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "model_source": model_source,
                "normalize": normalize,
            },
            storage_hint="session",
            suggested_name=f"confusion_matrix_{model_identifier.replace(':', '_').replace('/', '_')}",
        )

    except Exception as e:
        logger.exception(f"Error plotting confusion matrix: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error plotting confusion matrix: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

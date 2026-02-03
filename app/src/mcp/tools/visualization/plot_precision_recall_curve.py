"""Generate Precision-Recall curves for classification models."""

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.metrics import auc, average_precision_score, precision_recall_curve

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry
from src.utils.plotting import close_figure, save_plot_to_minio


@mcp.tool
@process_tool
@register_tool
async def plot_precision_recall_curve(
    dataset_id: str,
    model_source: dict,
    target_column: str,
    positive_class: int | str | None = None,
) -> str:
    """Generate Precision-Recall curve for classification models.

    Creates a PR curve showing the trade-off between precision and recall
    at various classification thresholds. Particularly useful for imbalanced
    datasets where ROC curves may be overly optimistic.

    Args:
        dataset_id: Entity ID of the dataset with true labels
        model_source: Model identifier:
            - {"run_id": "abc123"}
            - {"model_name": "my_model", "version": 2}
            - {"model_name": "my_model", "stage": "Production"}
        target_column: Name of the column containing true labels
        positive_class: Which class to treat as positive (auto-detected if None)

    Returns:
        ToolResponse with PR curve plot and AP score

    Example:
        "Show precision-recall curve for the classifier"
        → plot_precision_recall_curve(
            dataset_id="test_data_123",
            model_source={"model_name": "classifier", "stage": "Production"},
            target_column="label"
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
                summary=f"Error: Target column '{target_column}' not found in dataset",
                metadata={"error": "ColumnNotFound", "column": target_column},
                storage_hint="never",
            )

        y_true = df[target_column]

        # Check if binary
        unique_classes = y_true.unique()
        if len(unique_classes) != 2:
            return ToolResponse(
                payload=None,
                summary=f"Error: PR curve requires binary classification (found {len(unique_classes)} classes)",
                metadata={"error": "NotBinaryClassification", "n_classes": len(unique_classes)},
                storage_hint="never",
            )

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

        # Make predictions (need probability scores)
        try:
            # Try to get predict_proba first
            if hasattr(model, "predict_proba"):
                y_proba = model.predict_proba(df)
            else:
                # Use regular predict and hope it returns probabilities
                predictions = model.predict(df)

                if isinstance(predictions, pd.DataFrame):
                    # Look for probability column
                    prob_cols = [col for col in predictions.columns if "prob" in col.lower() or "score" in col.lower()]
                    if prob_cols:
                        y_proba = predictions[prob_cols[0]].values
                    else:
                        y_proba = predictions.values
                else:
                    y_proba = np.array(predictions)

            # Ensure we have probability scores
            if isinstance(y_proba, np.ndarray) and len(y_proba.shape) == 2:
                # Binary classification probabilities (n_samples, 2)
                y_scores = y_proba[:, 1]  # Probability of positive class
            elif isinstance(y_proba, np.ndarray) and len(y_proba.shape) == 1:
                # Already single column of scores
                y_scores = y_proba
            else:
                return ToolResponse(
                    payload=None,
                    summary="Error: Could not extract probability scores from model predictions",
                    metadata={"error": "PredictionFormatError"},
                    storage_hint="never",
                )

        except Exception as e:
            logger.exception(f"Error making predictions: {e}")
            return ToolResponse(
                payload=None,
                summary=f"Error making predictions: {e}",
                metadata={"error": "PredictionError", "details": str(e)},
                storage_hint="never",
            )

        # Determine positive class
        if positive_class is None:
            positive_class = sorted(unique_classes)[1]  # Use second class as positive

        # Encode labels as binary (0/1)
        y_binary = (y_true == positive_class).astype(int)

        # Compute PR curve
        precision, recall, thresholds = precision_recall_curve(y_binary, y_scores)
        pr_auc = auc(recall, precision)
        average_precision = average_precision_score(y_binary, y_scores)

        # Compute baseline (random classifier)
        baseline = (y_binary == 1).sum() / len(y_binary)

        # Create plot
        fig, ax = plt.subplots(figsize=(8, 8))

        ax.plot(recall, precision, color="darkorange", lw=2, label=f"PR curve (AP = {average_precision:.3f})")
        ax.axhline(y=baseline, color="navy", lw=2, linestyle="--", label=f"Baseline (random) = {baseline:.3f}")

        ax.set_xlim([0.0, 1.0])
        ax.set_ylim([0.0, 1.05])
        ax.set_xlabel("Recall")
        ax.set_ylabel("Precision")
        ax.set_title(f"Precision-Recall Curve: {model_identifier}")
        ax.legend(loc="lower left")
        ax.grid(alpha=0.3)

        plt.tight_layout()

        # Save plot
        object_key, plot_url = await save_plot_to_minio(
            fig, f"pr_curve_{model_identifier.replace(':', '_').replace('/', '_')}"
        )
        close_figure(fig)

        # Find optimal threshold (F1 score)
        f1_scores = 2 * (precision[:-1] * recall[:-1]) / (precision[:-1] + recall[:-1] + 1e-10)
        optimal_idx = np.argmax(f1_scores)
        optimal_threshold = thresholds[optimal_idx]
        optimal_precision = precision[optimal_idx]
        optimal_recall = recall[optimal_idx]
        optimal_f1 = f1_scores[optimal_idx]

        # Generate summary
        summary = "📊 Precision-Recall Curve Analysis\n\n"
        summary += f"Model: {model_identifier}\n"
        summary += f"Dataset: {len(df):,} samples\n"
        summary += f"Positive Class: {positive_class}\n"
        summary += f"Class Balance: {baseline:.2%} positive\n\n"

        summary += "Performance:\n"
        summary += f"  • Average Precision (AP): {average_precision:.4f}\n"
        summary += f"  • PR AUC: {pr_auc:.4f}\n"
        summary += f"  • Baseline: {baseline:.4f}\n\n"

        summary += "Optimal Threshold (max F1):\n"
        summary += f"  • Threshold: {optimal_threshold:.4f}\n"
        summary += f"  • Precision: {optimal_precision:.4f}\n"
        summary += f"  • Recall: {optimal_recall:.4f}\n"
        summary += f"  • F1 Score: {optimal_f1:.4f}\n\n"

        # Interpretation
        if average_precision >= 0.9:
            interpretation = "Excellent"
        elif average_precision >= 0.8:
            interpretation = "Good"
        elif average_precision >= 0.7:
            interpretation = "Fair"
        elif average_precision >= 0.6:
            interpretation = "Poor"
        else:
            interpretation = "Very Poor"

        summary += f"Model Quality: {interpretation}\n\n"

        # Note about imbalanced data
        if baseline < 0.3 or baseline > 0.7:
            summary += "⚠️  Note: Dataset is imbalanced. PR curve is more informative than ROC for this case.\n\n"

        summary += f"🖼️ Plot URL: {plot_url}\n"

        result_data = {
            "model_identifier": model_identifier,
            "model_uri": model_uri,
            "average_precision": float(average_precision),
            "pr_auc": float(pr_auc),
            "baseline": float(baseline),
            "precision": precision.tolist(),
            "recall": recall.tolist(),
            "thresholds": thresholds.tolist(),
            "optimal_threshold": float(optimal_threshold),
            "optimal_precision": float(optimal_precision),
            "optimal_recall": float(optimal_recall),
            "optimal_f1": float(optimal_f1),
            "positive_class": str(positive_class),
            "plot_url": plot_url,
            "plot_object_key": object_key,
        }

        return ToolResponse(
            payload=result_data,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "model_source": model_source,
                "average_precision": float(average_precision),
            },
            storage_hint="session",
            suggested_name=f"pr_curve_{model_identifier.replace(':', '_').replace('/', '_')}",
        )

    except Exception as e:
        logger.exception(f"Error plotting PR curve: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error plotting PR curve: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

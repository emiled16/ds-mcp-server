"""Generate feature importance plots from trained models."""

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.utils.plotting import close_figure, save_plot_to_minio


@mcp.tool
@process_tool
@register_tool
async def plot_feature_importance(
    model_source: dict,
    top_n: int = 20,
    plot_type: str = "bar",
) -> str:
    """Generate a feature importance plot from a trained model.

    Creates a visualization showing which features are most important
    for the model's predictions. Works with tree-based models that
    have feature_importances_ attribute.

    Args:
        model_source: Model identifier:
            - {"run_id": "abc123"}
            - {"model_name": "my_model", "version": 2}
            - {"model_name": "my_model", "stage": "Production"}
        top_n: Number of top features to display (default: 20)
        plot_type: Type of plot - "bar" or "barh" (horizontal) (default: "bar")

    Returns:
        ToolResponse with plot URL and feature importance data

    Example:
        "Show me the feature importance for the production XGBoost model"
        → plot_feature_importance(
            model_source={"model_name": "xgboost_model", "stage": "Production"},
            top_n=15
        )
    """
    try:
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
        try:
            # Load the underlying sklearn/xgboost model
            model = mlflow.sklearn.load_model(model_uri)
        except Exception:
            # Fallback to pyfunc
            model = mlflow.pyfunc.load_model(model_uri)
            # Try to unwrap the model
            if hasattr(model, "_model_impl"):
                model = model._model_impl.sklearn_model

        # Get feature importances
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
        elif hasattr(model, "coef_"):
            # For linear models, use absolute coefficients
            importances = np.abs(model.coef_)
            if len(importances.shape) > 1:
                # Multi-class, take mean across classes
                importances = importances.mean(axis=0)
        else:
            return ToolResponse(
                payload=None,
                summary="Error: Model does not have feature importances or coefficients",
                metadata={"error": "AttributeError", "model_type": type(model).__name__},
                storage_hint="never",
            )

        # Get feature names
        if hasattr(model, "feature_names_in_"):
            feature_names = model.feature_names_in_
        else:
            # Generate generic names
            feature_names = [f"feature_{i}" for i in range(len(importances))]

        # Create DataFrame and sort
        importance_df = pd.DataFrame(
            {
                "feature": feature_names,
                "importance": importances,
            }
        )
        importance_df = importance_df.sort_values("importance", ascending=False)

        # Limit to top N
        top_features = importance_df.head(top_n)

        # Create plot
        fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.3)))

        if plot_type == "barh":
            # Horizontal bar chart (better for many features)
            ax.barh(range(len(top_features)), top_features["importance"].values, color="steelblue")
            ax.set_yticks(range(len(top_features)))
            ax.set_yticklabels(top_features["feature"].values)
            ax.invert_yaxis()  # Highest importance at top
            ax.set_xlabel("Importance")
            ax.set_ylabel("Feature")
        else:
            # Vertical bar chart
            ax.bar(range(len(top_features)), top_features["importance"].values, color="steelblue")
            ax.set_xticks(range(len(top_features)))
            ax.set_xticklabels(top_features["feature"].values, rotation=45, ha="right")
            ax.set_ylabel("Importance")
            ax.set_xlabel("Feature")

        ax.set_title(f"Feature Importance: {model_identifier}")
        ax.grid(axis="x" if plot_type == "barh" else "y", alpha=0.3)
        plt.tight_layout()

        # Save plot
        object_key, plot_url = save_plot_to_minio(
            fig, f"feature_importance_{model_identifier.replace(':', '_').replace('/', '_')}"
        )
        close_figure(fig)

        # Generate summary
        summary = "📊 Feature Importance Plot\n\n"
        summary += f"Model: {model_identifier}\n"
        summary += f"Top {len(top_features)} Features:\n\n"

        for idx, row in top_features.head(10).iterrows():
            summary += f"  {idx + 1}. {row['feature']}: {row['importance']:.4f}\n"

        if len(top_features) > 10:
            summary += f"\n  ... and {len(top_features) - 10} more features\n"

        summary += f"\n🖼️ Plot URL: {plot_url}\n"

        result_data = {
            "model_identifier": model_identifier,
            "model_uri": model_uri,
            "feature_importances": importance_df.to_dict(orient="records"),
            "top_features": top_features.to_dict(orient="records"),
            "plot_url": plot_url,
            "plot_object_key": object_key,
        }

        return ToolResponse(
            payload=result_data,
            summary=summary,
            metadata={
                "model_source": model_source,
                "top_n": top_n,
                "plot_type": plot_type,
            },
            storage_hint="session",
            suggested_name=f"feature_importance_{model_identifier.replace(':', '_').replace('/', '_')}",
        )

    except Exception as e:
        logger.exception(f"Error plotting feature importance: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error plotting feature importance: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

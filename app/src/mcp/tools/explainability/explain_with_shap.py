"""SHAP (SHapley Additive exPlanations) model explainability tool."""

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry
from src.utils.plotting import save_plot_to_minio


@mcp.tool
@process_tool
@register_tool
async def explain_with_shap(
    dataset_id: str,
    run_id: str | None = None,
    model_name: str | None = None,
    model_version: str | None = None,
    model_stage: str | None = None,
    max_samples: int = 100,
    plot_type: str = "summary",
) -> str:
    """Explain model predictions using SHAP values.

    SHAP (SHapley Additive exPlanations) provides a unified measure of feature
    importance based on game theory. It assigns each feature an importance value
    for a particular prediction.

    Supports multiple SHAP plot types:
    - summary: Beeswarm plot showing feature importance and effects
    - bar: Bar plot of mean absolute SHAP values
    - waterfall: Waterfall plot for a single prediction (uses first sample)
    - force: Force plot for a single prediction (uses first sample)

    Args:
        dataset_id: Entity ID of the dataset to explain
        run_id: MLflow run ID (if loading by run)
        model_name: Registered model name (if loading from registry)
        model_version: Model version number (requires model_name)
        model_stage: Model stage - "Staging", "Production" (requires model_name)
        max_samples: Maximum number of samples to use for SHAP calculation (default: 100)
        plot_type: Type of SHAP plot - "summary", "bar", "waterfall", "force"

    Returns:
        ToolResponse with SHAP explanation plot and values

    Example:
        "Explain model predictions using SHAP"
        → explain_with_shap(
            dataset_id="test_data_123",
            run_id="abc123"
        )

        "Create SHAP waterfall plot for production model"
        → explain_with_shap(
            dataset_id="test_data_123",
            model_name="sales_predictor",
            model_stage="Production",
            plot_type="waterfall"
        )
    """
    try:
        # Import SHAP (only when needed)
        try:
            import shap
        except ImportError:
            return ToolResponse(
                payload=None,
                summary="Error: SHAP library not installed. Install with: pip install shap",
                metadata={"error": "MissingDependency", "package": "shap"},
                storage_hint="never",
            )

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

        # Load model
        model = None
        model_info = {}

        if run_id:
            logger.info(f"Loading model from run {run_id}")
            model_uri = f"runs:/{run_id}/model"
            model = mlflow.pyfunc.load_model(model_uri)
            model_info["source"] = "run"
            model_info["run_id"] = run_id

        elif model_name:
            if model_version:
                logger.info(f"Loading model {model_name} version {model_version}")
                model_uri = f"models:/{model_name}/{model_version}"
                model_info["source"] = "registry"
                model_info["model_name"] = model_name
                model_info["model_version"] = model_version
            elif model_stage:
                logger.info(f"Loading model {model_name} stage {model_stage}")
                model_uri = f"models:/{model_name}/{model_stage}"
                model_info["source"] = "registry"
                model_info["model_name"] = model_name
                model_info["model_stage"] = model_stage
            else:
                return ToolResponse(
                    payload=None,
                    summary="Error: Must specify either model_version or model_stage with model_name",
                    metadata={"error": "InvalidModelSpec"},
                    storage_hint="never",
                )

            model = mlflow.pyfunc.load_model(model_uri)

        else:
            return ToolResponse(
                payload=None,
                summary="Error: Must specify either run_id or model_name",
                metadata={"error": "MissingModelSpec"},
                storage_hint="never",
            )

        # Sample data if needed
        if len(df) > max_samples:
            logger.info(f"Sampling {max_samples} rows from {len(df)} total rows")
            X = df.sample(n=max_samples, random_state=42)
        else:
            X = df

        logger.info(f"Computing SHAP values for {len(X)} samples")

        # Create SHAP explainer
        # Use KernelExplainer for model-agnostic explanations
        explainer = shap.KernelExplainer(model.predict, X)
        shap_values = explainer.shap_values(X)

        # Handle multi-output models
        if isinstance(shap_values, list):
            # For classification with multiple classes, use first class
            shap_values = shap_values[0]

        # Create plot
        fig, ax = plt.subplots(figsize=(10, 6))

        if plot_type == "summary":
            shap.summary_plot(shap_values, X, show=False)
            plot_title = "SHAP Summary Plot"

        elif plot_type == "bar":
            shap.summary_plot(shap_values, X, plot_type="bar", show=False)
            plot_title = "SHAP Feature Importance"

        elif plot_type == "waterfall":
            # Waterfall plot for first sample
            shap.waterfall_plot(
                shap.Explanation(
                    values=shap_values[0],
                    base_values=explainer.expected_value,
                    data=X.iloc[0],
                    feature_names=X.columns.tolist(),
                ),
                show=False,
            )
            plot_title = "SHAP Waterfall Plot (Sample 0)"

        elif plot_type == "force":
            # Force plot for first sample
            shap.force_plot(explainer.expected_value, shap_values[0], X.iloc[0], matplotlib=True, show=False)
            plot_title = "SHAP Force Plot (Sample 0)"

        else:
            plt.close(fig)
            return ToolResponse(
                payload=None,
                summary=f"Error: Invalid plot_type '{plot_type}'. Must be 'summary', 'bar', 'waterfall', or 'force'",
                metadata={"error": "InvalidPlotType"},
                storage_hint="never",
            )

        plt.title(plot_title)
        plt.tight_layout()

        # Save plot
        _, plot_url = await save_plot_to_minio(fig, f"shap_{plot_type}")
        plt.close(fig)

        # Calculate feature importance from SHAP values
        feature_importance = {}
        mean_abs_shap = np.abs(shap_values).mean(axis=0)

        for i, col in enumerate(X.columns):
            feature_importance[col] = float(mean_abs_shap[i])

        # Sort by importance
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)

        # Build result
        result = {
            "plot_type": plot_type,
            "plot_url": plot_url,
            "n_samples": len(X),
            "n_features": len(X.columns),
            "feature_importance": dict(sorted_features),
            "base_value": float(explainer.expected_value),
            "model_info": model_info,
        }

        # Generate summary
        summary = "🔍 SHAP Explanation\n\n"
        summary += f"Plot Type: {plot_type}\n"
        summary += f"Samples Analyzed: {len(X)}\n"
        summary += f"Features: {len(X.columns)}\n"
        summary += f"Base Value: {explainer.expected_value:.4f}\n\n"

        summary += "Top 10 Most Important Features (by mean |SHAP value|):\n"
        for i, (feature, importance) in enumerate(sorted_features[:10], 1):
            summary += f"  {i}. {feature}: {importance:.4f}\n"

        summary += f"\n📊 Plot: {plot_url}\n\n"

        summary += "Interpretation:\n"
        summary += "  • SHAP values represent the contribution of each feature to the prediction\n"
        summary += "  • Positive SHAP values push the prediction higher\n"
        summary += "  • Negative SHAP values push the prediction lower\n"
        summary += f"  • Base value ({explainer.expected_value:.4f}) is the average model output\n"

        if plot_type == "summary":
            summary += "  • Summary plot shows distribution of SHAP values for each feature\n"
            summary += "  • Color represents feature value (red=high, blue=low)\n"
        elif plot_type == "bar":
            summary += "  • Bar plot shows mean absolute SHAP value (global importance)\n"
        elif plot_type in ["waterfall", "force"]:
            summary += f"  • {plot_type.title()} plot shows how features contribute to a single prediction\n"

        return ToolResponse(
            payload=result,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "plot_type": plot_type,
                **model_info,
            },
            storage_hint="session",
            suggested_name=f"shap_{plot_type}",
        )

    except Exception as e:
        logger.exception(f"Error computing SHAP explanation: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error computing SHAP explanation: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

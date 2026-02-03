"""Partial dependence plot (PDP) tool for model explainability."""

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.inspection import partial_dependence

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry
from src.utils.plotting import save_plot_to_minio


@mcp.tool
@process_tool
@register_tool
async def plot_partial_dependence(
    dataset_id: str,
    features: list[str],
    run_id: str | None = None,
    model_name: str | None = None,
    model_version: str | None = None,
    model_stage: str | None = None,
    grid_resolution: int = 50,
    percentiles: tuple[float, float] = (0.05, 0.95),
) -> str:
    """Plot partial dependence of model predictions on features.

    Partial dependence plots (PDPs) show the marginal effect of one or two
    features on the predicted outcome. They help visualize the relationship
    between features and predictions while averaging out the effects of all
    other features.

    Args:
        dataset_id: Entity ID of the dataset
        features: List of feature names to plot (max 4 features for readability)
        run_id: MLflow run ID (if loading by run)
        model_name: Registered model name (if loading from registry)
        model_version: Model version number (requires model_name)
        model_stage: Model stage - "Staging", "Production" (requires model_name)
        grid_resolution: Number of grid points for each feature (default: 50)
        percentiles: Percentile range to use for feature values (default: (0.05, 0.95))

    Returns:
        ToolResponse with partial dependence plots

    Example:
        "Show how revenue depends on price and marketing spend"
        → plot_partial_dependence(
            dataset_id="sales_data_123",
            features=["price", "marketing_spend"],
            run_id="abc123"
        )

        "Create PDP for top 3 features using production model"
        → plot_partial_dependence(
            dataset_id="test_data_123",
            features=["feature1", "feature2", "feature3"],
            model_name="predictor",
            model_stage="Production"
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

        # Validate features
        if not features or len(features) == 0:
            return ToolResponse(
                payload=None,
                summary="Error: Must specify at least one feature",
                metadata={"error": "MissingFeatures"},
                storage_hint="never",
            )

        if len(features) > 4:
            return ToolResponse(
                payload=None,
                summary=f"Error: Too many features ({len(features)}). Maximum is 4 for readability.",
                metadata={"error": "TooManyFeatures"},
                storage_hint="never",
            )

        for feature in features:
            if feature not in df.columns:
                return ToolResponse(
                    payload=None,
                    summary=f"Error: Feature '{feature}' not found in dataset",
                    metadata={"error": "FeatureNotFound", "feature": feature},
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

        logger.info(f"Computing partial dependence for features: {features}")

        # Get feature indices
        feature_indices = [df.columns.get_loc(f) for f in features]

        # Create sklearn-compatible wrapper for MLflow model
        class MLflowWrapper:
            def __init__(self, mlflow_model, feature_names):
                self.mlflow_model = mlflow_model
                self.feature_names = feature_names

            def predict(self, X):
                if isinstance(X, np.ndarray):
                    X = pd.DataFrame(X, columns=self.feature_names)
                return self.mlflow_model.predict(X)

        wrapped_model = MLflowWrapper(model, df.columns.tolist())

        # Compute partial dependence
        pd_result = partial_dependence(
            wrapped_model,
            X=df,
            features=feature_indices,
            grid_resolution=grid_resolution,
            percentiles=percentiles,
        )

        # Create plots
        n_features = len(features)
        fig, axes = plt.subplots(1, n_features, figsize=(6 * n_features, 5))

        if n_features == 1:
            axes = [axes]

        for idx, (ax, feature_idx, feature_name) in enumerate(zip(axes, feature_indices, features)):
            # Plot PDP
            ax.plot(pd_result["grid_values"][idx], pd_result["average"][idx], linewidth=2)
            ax.set_xlabel(feature_name, fontsize=12)
            ax.set_ylabel("Partial Dependence", fontsize=12)
            ax.set_title(f"PDP for {feature_name}", fontsize=14)
            ax.grid(alpha=0.3)

            # Add rug plot (data distribution)
            deciles = np.percentile(df[feature_name], np.arange(0, 101, 10))
            ax.plot(
                deciles,
                [pd_result["average"][idx].min()] * len(deciles),
                "|",
                color="red",
                markersize=10,
                alpha=0.5,
                label="Deciles",
            )

        plt.tight_layout()

        # Save plot
        _, plot_url = await save_plot_to_minio(fig, "partial_dependence")
        plt.close(fig)

        # Extract PDP data for each feature
        pdp_data = {}
        for idx, feature_name in enumerate(features):
            pdp_data[feature_name] = {
                "grid_values": pd_result["grid_values"][idx].tolist(),
                "average_predictions": pd_result["average"][idx].tolist(),
                "feature_range": [
                    float(pd_result["grid_values"][idx].min()),
                    float(pd_result["grid_values"][idx].max()),
                ],
                "effect_range": [float(pd_result["average"][idx].min()), float(pd_result["average"][idx].max())],
            }

        # Build result
        result = {
            "features": features,
            "pdp_data": pdp_data,
            "grid_resolution": grid_resolution,
            "percentiles": percentiles,
            "plot_url": plot_url,
            "model_info": model_info,
        }

        # Generate summary
        summary = "📊 Partial Dependence Plot\n\n"
        summary += f"Features Analyzed: {', '.join(features)}\n"
        summary += f"Grid Resolution: {grid_resolution} points\n"
        summary += f"Percentile Range: {percentiles[0]:.0%} - {percentiles[1]:.0%}\n\n"

        summary += "Partial Dependence Effects:\n"
        for feature_name, data in pdp_data.items():
            effect_size = data["effect_range"][1] - data["effect_range"][0]
            summary += f"\n  • {feature_name}:\n"
            summary += f"    - Feature range: [{data['feature_range'][0]:.4f}, {data['feature_range'][1]:.4f}]\n"
            summary += f"    - Effect range: [{data['effect_range'][0]:.4f}, {data['effect_range'][1]:.4f}]\n"
            summary += f"    - Total effect size: {effect_size:.4f}\n"

            # Identify trend
            avg_preds = np.array(data["average_predictions"])
            if len(avg_preds) > 1:
                slope = np.polyfit(range(len(avg_preds)), avg_preds, 1)[0]
                if abs(slope) < 0.001:
                    trend = "flat (minimal effect)"
                elif slope > 0:
                    trend = "increasing (positive effect)"
                else:
                    trend = "decreasing (negative effect)"
                summary += f"    - Trend: {trend}\n"

        summary += f"\n📊 Plot: {plot_url}\n\n"

        summary += "Interpretation:\n"
        summary += "  • Partial dependence shows how predictions change as each feature varies\n"
        summary += "  • Other features are held at their average values\n"
        summary += "  • Steep slopes indicate strong feature effects\n"
        summary += "  • Flat lines indicate weak or no effect\n"
        summary += "  • Red markers show data distribution (deciles)\n"

        return ToolResponse(
            payload=result,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "features": features,
                **model_info,
            },
            storage_hint="session",
            suggested_name="partial_dependence",
        )

    except Exception as e:
        logger.exception(f"Error creating partial dependence plot: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error creating partial dependence plot: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

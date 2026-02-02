"""Feature contribution visualization tool."""

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
async def plot_feature_contributions(
    dataset_id: str,
    sample_index: int,
    run_id: str | None = None,
    model_name: str | None = None,
    model_version: str | None = None,
    model_stage: str | None = None,
    top_n: int = 10,
    method: str = "permutation",
) -> str:
    """Visualize feature contributions for a specific prediction.

    Shows how much each feature contributed to a specific prediction
    compared to the average prediction.

    Supported methods:
    - permutation: Measures contribution by permuting each feature
    - difference: Shows difference from mean for each feature

    Args:
        dataset_id: Entity ID of the dataset
        sample_index: Index of the sample to explain
        run_id: MLflow run ID (if loading by run)
        model_name: Registered model name (if loading from registry)
        model_version: Model version number (requires model_name)
        model_stage: Model stage - "Staging", "Production" (requires model_name)
        top_n: Number of top contributing features to show (default: 10)
        method: Contribution calculation method - "permutation" or "difference"

    Returns:
        ToolResponse with feature contribution plot

    Example:
        "Show feature contributions for prediction at row 42"
        → plot_feature_contributions(
            dataset_id="test_data_123",
            sample_index=42,
            run_id="abc123"
        )

        "Visualize top 5 feature contributions for first sample"
        → plot_feature_contributions(
            dataset_id="test_data_123",
            sample_index=0,
            model_name="predictor",
            model_stage="Production",
            top_n=5
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

        # Validate sample index
        if sample_index < 0 or sample_index >= len(df):
            return ToolResponse(
                payload=None,
                summary=f"Error: sample_index {sample_index} out of range [0, {len(df) - 1}]",
                metadata={"error": "InvalidSampleIndex"},
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

        logger.info(f"Computing feature contributions for sample {sample_index}")

        # Get sample and baseline
        sample = df.iloc[sample_index : sample_index + 1]
        baseline_prediction = float(model.predict(df).mean())
        sample_prediction = float(model.predict(sample)[0])

        contributions = {}

        if method == "permutation":
            # Permutation-based feature contribution
            for col in df.columns:
                # Create modified sample with feature set to mean
                modified_sample = sample.copy()
                modified_sample[col] = df[col].mean()

                # Get prediction with modified feature
                modified_prediction = float(model.predict(modified_sample)[0])

                # Contribution is difference in prediction
                contribution = sample_prediction - modified_prediction
                contributions[col] = contribution

        elif method == "difference":
            # Difference from mean baseline
            sample_values = sample.iloc[0]
            feature_means = df.mean()

            for col in df.columns:
                # Simple contribution based on deviation from mean
                # This is a simplified method and may not be accurate for all models
                feature_diff = sample_values[col] - feature_means[col]
                contributions[col] = feature_diff

        else:
            return ToolResponse(
                payload=None,
                summary=f"Error: Invalid method '{method}'. Must be 'permutation' or 'difference'",
                metadata={"error": "InvalidMethod"},
                storage_hint="never",
            )

        # Sort by absolute contribution
        sorted_contributions = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)

        # Take top N
        top_contributions = sorted_contributions[:top_n]

        # Create visualization
        fig, ax = plt.subplots(figsize=(10, 6))

        features = [f[0] for f in top_contributions]
        values = [f[1] for f in top_contributions]

        # Create horizontal bar plot
        colors = ["green" if v > 0 else "red" for v in values]
        y_pos = np.arange(len(features))

        ax.barh(y_pos, values, color=colors, alpha=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(features)
        ax.set_xlabel("Feature Contribution", fontsize=12)
        ax.set_title(f"Top {top_n} Feature Contributions for Sample {sample_index}", fontsize=14)
        ax.axvline(x=0, color="black", linestyle="-", linewidth=1)
        ax.grid(axis="x", alpha=0.3)

        # Add prediction info
        textstr = f"Prediction: {sample_prediction:.4f}\nBaseline: {baseline_prediction:.4f}"
        props = dict(boxstyle="round", facecolor="wheat", alpha=0.5)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10, verticalalignment="top", bbox=props)

        plt.tight_layout()

        # Save plot
        plot_url = await save_plot_to_minio(fig, "feature_contributions")
        plt.close(fig)

        # Build result
        result = {
            "sample_index": sample_index,
            "prediction": sample_prediction,
            "baseline_prediction": baseline_prediction,
            "deviation": sample_prediction - baseline_prediction,
            "feature_contributions": dict(sorted_contributions),
            "top_contributions": dict(top_contributions),
            "method": method,
            "plot_url": plot_url,
            "model_info": model_info,
            "sample_values": sample.iloc[0].to_dict(),
        }

        # Generate summary
        summary = f"🔍 Feature Contributions for Sample {sample_index}\n\n"
        summary += f"Prediction: {sample_prediction:.4f}\n"
        summary += f"Baseline (Average): {baseline_prediction:.4f}\n"
        summary += f"Deviation: {result['deviation']:+.4f}\n"
        summary += f"Method: {method}\n\n"

        summary += f"Top {top_n} Contributing Features:\n"
        for i, (feature, contribution) in enumerate(top_contributions, 1):
            direction = "↑" if contribution > 0 else "↓"
            summary += f"  {i}. {feature}: {contribution:+.4f} {direction}\n"

        summary += f"\n📊 Plot: {plot_url}\n\n"

        summary += "Interpretation:\n"
        summary += "  • Green bars: Features pushing prediction higher than baseline\n"
        summary += "  • Red bars: Features pushing prediction lower than baseline\n"

        if method == "permutation":
            summary += "  • Contributions computed by replacing each feature with its mean\n"
            summary += "  • Shows impact of each feature on this specific prediction\n"
        else:
            summary += "  • Contributions based on deviation from feature means\n"
            summary += "  • Simplified method; may not reflect true model behavior\n"

        return ToolResponse(
            payload=result,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "sample_index": sample_index,
                "prediction": sample_prediction,
                **model_info,
            },
            storage_hint="session",
            suggested_name=f"contributions_sample_{sample_index}",
        )

    except Exception as e:
        logger.exception(f"Error computing feature contributions: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error computing feature contributions: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

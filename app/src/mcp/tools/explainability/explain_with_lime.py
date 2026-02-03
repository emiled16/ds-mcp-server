"""LIME (Local Interpretable Model-agnostic Explanations) tool."""

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
async def explain_with_lime(
    dataset_id: str,
    sample_index: int,
    run_id: str | None = None,
    model_name: str | None = None,
    model_version: str | None = None,
    model_stage: str | None = None,
    num_features: int = 10,
    num_samples: int = 5000,
) -> str:
    """Explain individual predictions using LIME.

    LIME (Local Interpretable Model-agnostic Explanations) explains individual
    predictions by approximating the model locally with an interpretable model.

    Works by:
    1. Generating perturbed samples around the instance to explain
    2. Getting model predictions for these samples
    3. Fitting a simple linear model on the perturbed data
    4. Using the linear model's coefficients as feature importances

    Args:
        dataset_id: Entity ID of the dataset
        sample_index: Index of the sample to explain (row number in dataset)
        run_id: MLflow run ID (if loading by run)
        model_name: Registered model name (if loading from registry)
        model_version: Model version number (requires model_name)
        model_stage: Model stage - "Staging", "Production" (requires model_name)
        num_features: Number of top features to show in explanation (default: 10)
        num_samples: Number of perturbed samples to generate (default: 5000)

    Returns:
        ToolResponse with LIME explanation

    Example:
        "Explain why the model predicted this value for sample 42"
        → explain_with_lime(
            dataset_id="test_data_123",
            sample_index=42,
            run_id="abc123"
        )

        "Explain prediction for first sample using production model"
        → explain_with_lime(
            dataset_id="test_data_123",
            sample_index=0,
            model_name="revenue_predictor",
            model_stage="Production",
            num_features=5
        )
    """
    try:
        # Import LIME
        try:
            from lime import lime_tabular
        except ImportError:
            return ToolResponse(
                payload=None,
                summary="Error: LIME library not installed. Install with: pip install lime",
                metadata={"error": "MissingDependency", "package": "lime"},
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

        logger.info(f"Explaining prediction for sample {sample_index}")

        # Get sample to explain
        sample = df.iloc[sample_index : sample_index + 1]

        # Create LIME explainer
        explainer = lime_tabular.LimeTabularExplainer(
            training_data=df.values,
            feature_names=df.columns.tolist(),
            mode="regression",  # Default to regression
            verbose=False,
        )

        # Get prediction for the sample
        prediction = model.predict(sample)[0]

        # Generate explanation
        explanation = explainer.explain_instance(
            data_row=sample.values[0],
            predict_fn=lambda x: model.predict(pd.DataFrame(x, columns=df.columns)),
            num_features=num_features,
            num_samples=num_samples,
        )

        # Extract feature contributions
        feature_contributions = {}
        for feature, contribution in explanation.as_list():
            # Parse feature name (LIME returns strings like "feature_name <= value")
            feature_name = feature.split(" ")[0] if " " in feature else feature
            feature_contributions[feature_name] = contribution

        # Create visualization
        fig, ax = plt.subplots(figsize=(10, 6))

        # Get top features
        features = [f[0] for f in explanation.as_list()[:num_features]]
        contributions = [f[1] for f in explanation.as_list()[:num_features]]

        # Create horizontal bar plot
        colors = ["green" if c > 0 else "red" for c in contributions]
        y_pos = np.arange(len(features))

        ax.barh(y_pos, contributions, color=colors, alpha=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(features)
        ax.set_xlabel("Feature Contribution")
        ax.set_title(f"LIME Explanation for Sample {sample_index}")
        ax.axvline(x=0, color="black", linestyle="-", linewidth=0.5)
        ax.grid(axis="x", alpha=0.3)

        plt.tight_layout()

        # Save plot
        _, plot_url = await save_plot_to_minio(fig, "lime_explanation")
        plt.close(fig)

        # Build result
        result = {
            "sample_index": sample_index,
            "prediction": float(prediction),
            "feature_contributions": feature_contributions,
            "num_features": num_features,
            "num_samples": num_samples,
            "plot_url": plot_url,
            "model_info": model_info,
            "sample_values": sample.iloc[0].to_dict(),
        }

        # Generate summary
        summary = f"🔍 LIME Explanation for Sample {sample_index}\n\n"
        summary += f"Prediction: {prediction:.4f}\n"
        summary += f"Features Analyzed: {num_features}\n"
        summary += f"Perturbation Samples: {num_samples}\n\n"

        summary += "Top Feature Contributions:\n"
        sorted_contributions = sorted(feature_contributions.items(), key=lambda x: abs(x[1]), reverse=True)
        for i, (feature, contribution) in enumerate(sorted_contributions[:num_features], 1):
            direction = "↑" if contribution > 0 else "↓"
            summary += f"  {i}. {feature}: {contribution:+.4f} {direction}\n"

        summary += f"\n📊 Plot: {plot_url}\n\n"

        summary += "Interpretation:\n"
        summary += "  • Positive contributions push the prediction higher\n"
        summary += "  • Negative contributions push the prediction lower\n"
        summary += "  • LIME explains this specific prediction, not the global model\n"
        summary += f"  • Explanation based on {num_samples} perturbed samples around this instance\n"

        return ToolResponse(
            payload=result,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "sample_index": sample_index,
                "prediction": float(prediction),
                **model_info,
            },
            storage_hint="session",
            suggested_name=f"lime_sample_{sample_index}",
        )

    except Exception as e:
        logger.exception(f"Error computing LIME explanation: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error computing LIME explanation: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

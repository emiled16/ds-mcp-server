"""General-purpose prediction explanation tool."""

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
async def explain_prediction(
    dataset_id: str,
    sample_index: int,
    run_id: str | None = None,
    model_name: str | None = None,
    model_version: str | None = None,
    model_stage: str | None = None,
    include_similar: bool = True,
    n_similar: int = 5,
) -> str:
    """Explain a specific prediction with comprehensive analysis.

    Provides a multi-faceted explanation of why the model made a specific
    prediction, including:
    - The prediction value and confidence
    - Feature values for the sample
    - Comparison to similar samples
    - Feature deviations from average
    - Permutation-based feature importance for this prediction

    Args:
        dataset_id: Entity ID of the dataset
        sample_index: Index of the sample to explain
        run_id: MLflow run ID (if loading by run)
        model_name: Registered model name (if loading from registry)
        model_version: Model version number (requires model_name)
        model_stage: Model stage - "Staging", "Production" (requires model_name)
        include_similar: Whether to find and show similar samples (default: True)
        n_similar: Number of similar samples to show (default: 5)

    Returns:
        ToolResponse with comprehensive prediction explanation

    Example:
        "Explain why the model predicted this value for sample 42"
        → explain_prediction(
            dataset_id="test_data_123",
            sample_index=42,
            run_id="abc123"
        )

        "Explain prediction with comparison to similar cases"
        → explain_prediction(
            dataset_id="test_data_123",
            sample_index=0,
            model_name="predictor",
            model_stage="Production",
            n_similar=10
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

        logger.info(f"Explaining prediction for sample {sample_index}")

        # Get sample and predictions
        sample = df.iloc[sample_index : sample_index + 1]
        sample_prediction = float(model.predict(sample)[0])

        # Get all predictions for context
        all_predictions = model.predict(df)
        baseline_prediction = float(np.mean(all_predictions))
        prediction_std = float(np.std(all_predictions))

        # Calculate z-score
        z_score = (sample_prediction - baseline_prediction) / prediction_std if prediction_std > 0 else 0.0

        # Get feature values and deviations
        sample_values = sample.iloc[0]
        feature_means = df.mean()
        feature_stds = df.std()

        feature_analysis = {}
        for col in df.columns:
            value = float(sample_values[col])
            mean = float(feature_means[col])
            std = float(feature_stds[col])
            z = (value - mean) / std if std > 0 else 0.0

            feature_analysis[col] = {
                "value": value,
                "mean": mean,
                "std": std,
                "deviation": value - mean,
                "z_score": z,
                "percentile": float((df[col] <= value).sum() / len(df) * 100),
            }

        # Find similar samples (by Euclidean distance)
        similar_samples = None
        if include_similar:
            # Normalize features for distance calculation
            df_normalized = (df - df.mean()) / df.std()
            sample_normalized = (sample - df.mean()) / df.std()

            # Calculate distances
            distances = np.sqrt(((df_normalized - sample_normalized.values) ** 2).sum(axis=1))

            # Get indices of most similar samples (excluding the sample itself)
            similar_indices = distances.argsort()[1 : n_similar + 1]  # Skip first (itself)

            similar_samples = []
            for idx in similar_indices:
                similar_samples.append(
                    {
                        "index": int(idx),
                        "prediction": float(all_predictions[idx]),
                        "distance": float(distances[idx]),
                    }
                )

        # Calculate permutation-based feature importance
        feature_importance = {}
        for col in df.columns:
            modified_sample = sample.copy()
            modified_sample[col] = df[col].mean()
            modified_prediction = float(model.predict(modified_sample)[0])
            importance = abs(sample_prediction - modified_prediction)
            feature_importance[col] = importance

        # Sort features by importance
        sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)

        # Create visualization
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # 1. Prediction context
        ax = axes[0, 0]
        ax.hist(all_predictions, bins=30, alpha=0.7, edgecolor="black")
        ax.axvline(
            sample_prediction,
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"This prediction: {sample_prediction:.4f}",
        )
        ax.axvline(
            baseline_prediction, color="blue", linestyle="--", linewidth=2, label=f"Average: {baseline_prediction:.4f}"
        )
        ax.set_xlabel("Prediction Value")
        ax.set_ylabel("Frequency")
        ax.set_title("Prediction Distribution")
        ax.legend()
        ax.grid(alpha=0.3)

        # 2. Top feature importance
        ax = axes[0, 1]
        top_features = sorted_features[:10]
        features_list = [f[0] for f in top_features]
        importance_list = [f[1] for f in top_features]
        y_pos = np.arange(len(features_list))
        ax.barh(y_pos, importance_list, alpha=0.7, color="steelblue")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(features_list)
        ax.set_xlabel("Importance (Prediction Change)")
        ax.set_title("Top 10 Feature Importance")
        ax.grid(axis="x", alpha=0.3)

        # 3. Feature deviations
        ax = axes[1, 0]
        deviations = {k: v["z_score"] for k, v in feature_analysis.items()}
        sorted_deviations = sorted(deviations.items(), key=lambda x: abs(x[1]), reverse=True)[:10]
        features_list = [f[0] for f in sorted_deviations]
        z_scores = [f[1] for f in sorted_deviations]
        colors = ["green" if z > 0 else "red" for z in z_scores]
        y_pos = np.arange(len(features_list))
        ax.barh(y_pos, z_scores, color=colors, alpha=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(features_list)
        ax.set_xlabel("Z-Score (Deviations from Mean)")
        ax.set_title("Top 10 Feature Deviations")
        ax.axvline(x=0, color="black", linestyle="-", linewidth=0.5)
        ax.grid(axis="x", alpha=0.3)

        # 4. Similar samples
        ax = axes[1, 1]
        if similar_samples:
            indices = [s["index"] for s in similar_samples]
            predictions = [s["prediction"] for s in similar_samples]
            distances = [s["distance"] for s in similar_samples]

            x = np.arange(len(indices))
            ax.bar(x, predictions, alpha=0.7, color="lightblue", label="Similar samples")
            ax.axhline(sample_prediction, color="red", linestyle="--", linewidth=2, label="This prediction")
            ax.set_xticks(x)
            ax.set_xticklabels([f"#{i}" for i in indices], rotation=45)
            ax.set_ylabel("Prediction")
            ax.set_title(f"Top {n_similar} Most Similar Samples")
            ax.legend()
            ax.grid(axis="y", alpha=0.3)
        else:
            ax.text(0.5, 0.5, "Similar samples not computed", ha="center", va="center", transform=ax.transAxes)
            ax.axis("off")

        plt.tight_layout()

        # Save plot
        plot_url = await save_plot_to_minio(fig, "prediction_explanation")
        plt.close(fig)

        # Build result
        result = {
            "sample_index": sample_index,
            "prediction": sample_prediction,
            "baseline_prediction": baseline_prediction,
            "prediction_std": prediction_std,
            "prediction_z_score": z_score,
            "feature_analysis": feature_analysis,
            "feature_importance": dict(sorted_features),
            "similar_samples": similar_samples,
            "plot_url": plot_url,
            "model_info": model_info,
        }

        # Generate summary
        summary = f"🔍 Comprehensive Prediction Explanation for Sample {sample_index}\n\n"
        summary += f"Prediction: {sample_prediction:.4f}\n"
        summary += f"Baseline (Average): {baseline_prediction:.4f}\n"
        summary += f"Deviation: {sample_prediction - baseline_prediction:+.4f} ({z_score:+.2f} std devs)\n\n"

        # Prediction context
        if abs(z_score) > 2:
            summary += f"⚠️  This prediction is {'UNUSUALLY HIGH' if z_score > 0 else 'UNUSUALLY LOW'} (|z| > 2)\n\n"
        elif abs(z_score) > 1:
            summary += f"This prediction is {'moderately high' if z_score > 0 else 'moderately low'} (|z| > 1)\n\n"
        else:
            summary += "This prediction is typical (|z| ≤ 1)\n\n"

        summary += "Top 5 Most Important Features:\n"
        for i, (feature, importance) in enumerate(sorted_features[:5], 1):
            feat_info = feature_analysis[feature]
            summary += f"  {i}. {feature}:\n"
            summary += f"     • Value: {feat_info['value']:.4f} (mean: {feat_info['mean']:.4f})\n"
            summary += f"     • Deviation: {feat_info['deviation']:+.4f} ({feat_info['percentile']:.1f}th percentile)\n"
            summary += f"     • Importance: {importance:.4f}\n"

        if similar_samples:
            summary += f"\nMost Similar Samples (top {min(3, len(similar_samples))}):\n"
            for i, sim in enumerate(similar_samples[:3], 1):
                summary += f"  {i}. Sample #{sim['index']}: prediction={sim['prediction']:.4f}, distance={sim['distance']:.4f}\n"

        summary += f"\n📊 Visualization: {plot_url}\n\n"

        summary += "Interpretation:\n"
        summary += "  • Feature importance shows which features most affect this prediction\n"
        summary += "  • Feature deviations show which features are unusual for this sample\n"
        summary += "  • Similar samples show predictions for comparable cases\n"
        summary += "  • High importance + high deviation = strong driver of this prediction\n"

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
            suggested_name=f"explanation_sample_{sample_index}",
        )

    except Exception as e:
        logger.exception(f"Error explaining prediction: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error explaining prediction: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

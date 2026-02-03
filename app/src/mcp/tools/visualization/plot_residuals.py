"""Generate residual plots for regression models."""

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry
from src.utils.plotting import close_figure, save_plot_to_minio


@mcp.tool
@process_tool
@register_tool
async def plot_residuals(
    dataset_id: str,
    model_source: dict,
    target_column: str,
    plot_type: str = "all",
) -> str:
    """Generate residual plots for regression model diagnostics.

    Creates visualizations to assess regression model assumptions:
    - Residuals vs Predicted: Check for heteroscedasticity
    - Residuals histogram: Check for normality
    - Q-Q plot: Check for normal distribution
    - Residuals vs Actual: Check for systematic bias

    Args:
        dataset_id: Entity ID of the dataset with true values
        model_source: Model identifier:
            - {"run_id": "abc123"}
            - {"model_name": "my_model", "version": 2}
            - {"model_name": "my_model", "stage": "Production"}
        target_column: Name of the column containing true values
        plot_type: Type of plot - "all", "scatter", "hist", or "qq" (default: "all")

    Returns:
        ToolResponse with plot URL and residual statistics

    Example:
        "Show residual plots for the production regression model"
        → plot_residuals(
            dataset_id="test_data_123",
            model_source={"model_name": "regression_model", "stage": "Production"},
            target_column="price"
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

        # Calculate residuals
        residuals = y_true.values - y_pred
        standardized_residuals = (residuals - residuals.mean()) / residuals.std()

        # Create plots
        if plot_type == "all":
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            ax1, ax2, ax3, ax4 = axes.flatten()
        else:
            fig, ax = plt.subplots(figsize=(10, 6))

        # Plot 1: Residuals vs Predicted
        if plot_type in ["all", "scatter"]:
            ax_scatter = ax1 if plot_type == "all" else ax
            ax_scatter.scatter(y_pred, residuals, alpha=0.5, edgecolors="k", linewidths=0.5)
            ax_scatter.axhline(y=0, color="r", linestyle="--", linewidth=2)
            ax_scatter.set_xlabel("Predicted Values")
            ax_scatter.set_ylabel("Residuals")
            ax_scatter.set_title("Residuals vs Predicted")
            ax_scatter.grid(alpha=0.3)

        # Plot 2: Histogram of residuals
        if plot_type in ["all", "hist"]:
            ax_hist = ax2 if plot_type == "all" else ax
            ax_hist.hist(residuals, bins=30, edgecolor="black", alpha=0.7)
            ax_hist.axvline(x=0, color="r", linestyle="--", linewidth=2)
            ax_hist.set_xlabel("Residuals")
            ax_hist.set_ylabel("Frequency")
            ax_hist.set_title("Distribution of Residuals")
            ax_hist.grid(alpha=0.3)

        # Plot 3: Q-Q plot
        if plot_type in ["all", "qq"]:
            ax_qq = ax3 if plot_type == "all" else ax
            stats.probplot(residuals, dist="norm", plot=ax_qq)
            ax_qq.set_title("Q-Q Plot")
            ax_qq.grid(alpha=0.3)

        # Plot 4: Residuals vs Actual
        if plot_type == "all":
            ax4.scatter(y_true, residuals, alpha=0.5, edgecolors="k", linewidths=0.5)
            ax4.axhline(y=0, color="r", linestyle="--", linewidth=2)
            ax4.set_xlabel("Actual Values")
            ax4.set_ylabel("Residuals")
            ax4.set_title("Residuals vs Actual")
            ax4.grid(alpha=0.3)

        fig.suptitle(f"Residual Analysis: {model_identifier}", fontsize=14, y=1.00 if plot_type != "all" else 0.995)
        plt.tight_layout()

        # Save plot
        object_key, plot_url = await save_plot_to_minio(
            fig, f"residuals_{model_identifier.replace(':', '_').replace('/', '_')}"
        )
        close_figure(fig)

        # Calculate residual statistics
        residual_stats = {
            "mean": float(residuals.mean()),
            "std": float(residuals.std()),
            "min": float(residuals.min()),
            "max": float(residuals.max()),
            "median": float(np.median(residuals)),
            "q1": float(np.percentile(residuals, 25)),
            "q3": float(np.percentile(residuals, 75)),
        }

        # Shapiro-Wilk test for normality (if sample size is reasonable)
        if len(residuals) < 5000:
            shapiro_stat, shapiro_p = stats.shapiro(residuals)
            residual_stats["shapiro_stat"] = float(shapiro_stat)
            residual_stats["shapiro_p_value"] = float(shapiro_p)
            residual_stats["normal_distribution"] = shapiro_p > 0.05

        # Generate summary
        summary = "📊 Residual Analysis\n\n"
        summary += f"Model: {model_identifier}\n"
        summary += f"Dataset: {len(df):,} samples\n\n"

        summary += "Residual Statistics:\n"
        summary += f"  • Mean: {residual_stats['mean']:.4f}\n"
        summary += f"  • Std: {residual_stats['std']:.4f}\n"
        summary += f"  • Min: {residual_stats['min']:.4f}\n"
        summary += f"  • Max: {residual_stats['max']:.4f}\n"
        summary += f"  • Median: {residual_stats['median']:.4f}\n"
        summary += f"  • Q1: {residual_stats['q1']:.4f}\n"
        summary += f"  • Q3: {residual_stats['q3']:.4f}\n"

        if "shapiro_p_value" in residual_stats:
            summary += "\nNormality Test (Shapiro-Wilk):\n"
            summary += f"  • Statistic: {residual_stats['shapiro_stat']:.4f}\n"
            summary += f"  • P-value: {residual_stats['shapiro_p_value']:.4f}\n"
            summary += f"  • Normal distribution: {'Yes' if residual_stats['normal_distribution'] else 'No'} (α=0.05)\n"

        summary += f"\n🖼️ Plot URL: {plot_url}\n"

        result_data = {
            "model_identifier": model_identifier,
            "model_uri": model_uri,
            "residual_stats": residual_stats,
            "residuals": residuals.tolist(),
            "predictions": y_pred.tolist(),
            "actuals": y_true.tolist(),
            "plot_url": plot_url,
            "plot_object_key": object_key,
        }

        return ToolResponse(
            payload=result_data,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "model_source": model_source,
                "plot_type": plot_type,
            },
            storage_hint="session",
            suggested_name=f"residuals_{model_identifier.replace(':', '_').replace('/', '_')}",
        )

    except Exception as e:
        logger.exception(f"Error plotting residuals: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error plotting residuals: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

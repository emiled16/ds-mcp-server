"""Compare multiple models on the same dataset."""

import mlflow
import numpy as np
import pandas as pd
from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def compare_models(
    dataset_id: str,
    model_sources: list[dict],
    target_column: str,
    problem_type: str | None = None,
    model_names: list[str] | None = None,
) -> str:
    """Compare multiple models on the same dataset.

    Evaluates each model and provides side-by-side comparison of metrics.
    Automatically detects problem type if not specified.

    Args:
        dataset_id: Entity ID of the dataset for evaluation
        model_sources: List of model identifiers, each can be:
            - {"run_id": "abc123"}
            - {"model_name": "my_model", "version": 2}
            - {"model_name": "my_model", "stage": "Production"}
        target_column: Name of the column containing true labels
        problem_type: "regression" or "classification" (auto-detected if not specified)
        model_names: Optional list of friendly names for models (for display)

    Returns:
        ToolResponse with comparison DataFrame and summary

    Example:
        "Compare the production XGBoost model with the staging RandomForest model"
        → compare_models(
            dataset_id="test_data_123",
            model_sources=[
                {"model_name": "xgboost_model", "stage": "Production"},
                {"model_name": "rf_model", "stage": "Staging"}
            ],
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

        # Check target column
        if target_column not in df.columns:
            return ToolResponse(
                payload=None,
                summary=f"Error: Target column '{target_column}' not found in dataset. Available: {list(df.columns)}",
                metadata={"error": "ValidationError", "target_column": target_column},
                storage_hint="never",
            )

        # Validate we have at least 2 models
        if len(model_sources) < 2:
            return ToolResponse(
                payload=None,
                summary="Error: At least 2 models required for comparison",
                metadata={"error": "ValidationError"},
                storage_hint="never",
            )

        # Auto-detect problem type if needed
        y_true = df[target_column]
        if not problem_type:
            if pd.api.types.is_numeric_dtype(y_true):
                unique_ratio = len(y_true.unique()) / len(y_true)
                problem_type = "regression" if unique_ratio > 0.05 else "classification"
            else:
                problem_type = "classification"

        logger.info(f"Comparing {len(model_sources)} models on {len(df)} samples ({problem_type})")

        # Evaluate each model
        results = []
        predictions_dict = {}

        for idx, model_source in enumerate(model_sources):
            # Determine model identifier
            run_id = model_source.get("run_id")
            model_name = model_source.get("model_name")
            version = model_source.get("version")
            stage = model_source.get("stage")

            if run_id:
                model_uri = f"runs:/{run_id}/model"
                model_identifier = f"run:{run_id[:8]}"
            elif model_name:
                if version:
                    model_uri = f"models:/{model_name}/{version}"
                    model_identifier = f"{model_name} v{version}"
                elif stage:
                    model_uri = f"models:/{model_name}/{stage}"
                    model_identifier = f"{model_name} ({stage})"
                else:
                    # Get latest version
                    client = mlflow.tracking.MlflowClient()
                    latest_versions = client.get_latest_versions(model_name, stages=["None", "Staging", "Production"])
                    if not latest_versions:
                        logger.warning(f"No versions found for model '{model_name}', skipping")
                        continue
                    latest = max(latest_versions, key=lambda v: int(v.version))
                    model_uri = f"models:/{model_name}/{latest.version}"
                    model_identifier = f"{model_name} v{latest.version}"
            else:
                logger.warning(f"Invalid model_source at index {idx}, skipping")
                continue

            # Use custom name if provided
            if model_names and idx < len(model_names):
                display_name = model_names[idx]
            else:
                display_name = model_identifier

            # Load model
            try:
                logger.info(f"Loading model: {model_uri}")
                model = mlflow.pyfunc.load_model(model_uri)
            except Exception as e:
                logger.exception(f"Error loading model {model_identifier}: {e}")
                results.append(
                    {
                        "model": display_name,
                        "error": f"Failed to load: {e}",
                    }
                )
                continue

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

                predictions_dict[display_name] = y_pred

            except Exception as e:
                logger.exception(f"Error making predictions with {model_identifier}: {e}")
                results.append(
                    {
                        "model": display_name,
                        "error": f"Prediction failed: {e}",
                    }
                )
                continue

            # Calculate metrics
            metrics = {"model": display_name}

            try:
                if problem_type == "regression":
                    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

                    metrics["mse"] = float(mean_squared_error(y_true, y_pred))
                    metrics["rmse"] = float(np.sqrt(metrics["mse"]))
                    metrics["mae"] = float(mean_absolute_error(y_true, y_pred))
                    metrics["r2"] = float(r2_score(y_true, y_pred))
                else:  # classification
                    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

                    unique_classes = np.unique(y_true)
                    n_classes = len(unique_classes)

                    metrics["accuracy"] = float(accuracy_score(y_true, y_pred))

                    if n_classes == 2:
                        metrics["precision"] = float(precision_score(y_true, y_pred, zero_division=0))
                        metrics["recall"] = float(recall_score(y_true, y_pred, zero_division=0))
                        metrics["f1"] = float(f1_score(y_true, y_pred, zero_division=0))
                    else:
                        metrics["precision_macro"] = float(
                            precision_score(y_true, y_pred, average="macro", zero_division=0)
                        )
                        metrics["recall_macro"] = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
                        metrics["f1_macro"] = float(f1_score(y_true, y_pred, average="macro", zero_division=0))

                results.append(metrics)

            except Exception as e:
                logger.exception(f"Error calculating metrics for {model_identifier}: {e}")
                metrics["error"] = f"Metrics failed: {e}"
                results.append(metrics)

        # Create comparison DataFrame
        if not results:
            return ToolResponse(
                payload=None,
                summary="Error: No models could be evaluated successfully",
                metadata={"error": "EvaluationError"},
                storage_hint="never",
            )

        comparison_df = pd.DataFrame(results)

        # Find best model for each metric
        best_models = {}
        metric_columns = [col for col in comparison_df.columns if col not in ["model", "error"]]

        for metric in metric_columns:
            if metric in comparison_df.columns:
                valid_rows = comparison_df[comparison_df[metric].notna()]
                if not valid_rows.empty:
                    # For most metrics, higher is better (except mse, rmse, mae)
                    if metric in ["mse", "rmse", "mae"]:
                        best_idx = valid_rows[metric].idxmin()
                    else:
                        best_idx = valid_rows[metric].idxmax()
                    best_models[metric] = comparison_df.loc[best_idx, "model"]

        # Generate summary
        summary = "📊 Model Comparison Results\n\n"
        summary += f"Dataset: {len(df):,} samples\n"
        summary += f"Problem Type: {problem_type.title()}\n"
        summary += f"Models Compared: {len(results)}\n\n"

        summary += "Metrics Comparison:\n"
        summary += comparison_df.to_string(index=False)
        summary += "\n\n"

        if best_models:
            summary += "Best Models by Metric:\n"
            for metric, model in best_models.items():
                summary += f"  • {metric}: {model}\n"

        # Overall winner (most best metrics)
        if best_models:
            from collections import Counter

            winner_counts = Counter(best_models.values())
            overall_winner = winner_counts.most_common(1)[0][0]
            wins = winner_counts[overall_winner]
            summary += f"\n🏆 Overall Winner: {overall_winner} (best in {wins}/{len(best_models)} metrics)\n"

        result_data = {
            "comparison": comparison_df.to_dict(orient="records"),
            "best_models": best_models,
            "problem_type": problem_type,
            "n_models": len(results),
            "n_samples": len(df),
        }

        return ToolResponse(
            payload=result_data,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "problem_type": problem_type,
                "n_models": len(results),
            },
            storage_hint="session",
            suggested_name=f"model_comparison_{len(results)}_models",
        )

    except Exception as e:
        logger.exception(f"Error comparing models: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error comparing models: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

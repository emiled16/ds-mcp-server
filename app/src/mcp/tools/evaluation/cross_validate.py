"""Perform K-fold cross-validation on a model."""

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import KFold, StratifiedKFold

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry
from src.workers.training import create_model


@mcp.tool
@process_tool
@register_tool
async def cross_validate(
    dataset_id: str,
    model_type: str,
    target_column: str,
    feature_columns: list[str] | None = None,
    hyperparameters: dict | None = None,
    n_folds: int = 5,
    stratified: bool = True,
    random_state: int = 42,
) -> str:
    """Perform K-fold cross-validation to assess model performance robustness.

    Trains the model on K different train/validation splits and reports
    aggregated metrics (mean ± std) across all folds.

    Args:
        dataset_id: Entity ID of the dataset
        model_type: Model type (xgboost, random_forest, gradient_boosting, linear)
        target_column: Name of the target column
        feature_columns: List of feature columns (uses all numeric if not specified)
        hyperparameters: Model hyperparameters (optional)
        n_folds: Number of folds for cross-validation (default: 5)
        stratified: Use stratified K-fold for classification (default: True)
        random_state: Random seed for reproducibility (default: 42)

    Returns:
        ToolResponse with cross-validation results

    Example:
        "Cross-validate XGBoost on the sales data with 5 folds"
        → cross_validate(
            dataset_id="sales_data_123",
            model_type="xgboost",
            target_column="revenue",
            n_folds=5
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

        # Determine feature columns
        if feature_columns is None:
            feature_columns = [
                col for col in df.columns if col != target_column and pd.api.types.is_numeric_dtype(df[col])
            ]

        if not feature_columns:
            return ToolResponse(
                payload=None,
                summary="Error: No feature columns available",
                metadata={"error": "ValidationError"},
                storage_hint="never",
            )

        # Check feature columns exist
        missing_cols = [col for col in feature_columns if col not in df.columns]
        if missing_cols:
            return ToolResponse(
                payload=None,
                summary=f"Error: Feature columns not found: {missing_cols}",
                metadata={"error": "ValidationError", "missing_columns": missing_cols},
                storage_hint="never",
            )

        # Prepare data
        X = df[feature_columns]
        y = df[target_column]

        # Auto-detect problem type
        if pd.api.types.is_numeric_dtype(y):
            unique_ratio = len(y.unique()) / len(y)
            problem_type = "regression" if unique_ratio > 0.05 else "classification"
        else:
            problem_type = "classification"

        logger.info(f"Starting {n_folds}-fold cross-validation for {model_type} ({problem_type})")

        # Choose cross-validation strategy
        if problem_type == "classification" and stratified:
            cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=random_state)
        else:
            cv = KFold(n_splits=n_folds, shuffle=True, random_state=random_state)

        # Store fold results
        fold_results = []

        for fold_idx, (train_idx, val_idx) in enumerate(
            cv.split(X, y if problem_type == "classification" else None), 1
        ):
            logger.info(f"Training fold {fold_idx}/{n_folds}")

            # Split data
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            # Create and train model
            try:
                model = create_model(
                    model_type=model_type,
                    hyperparameters=hyperparameters or {},
                )

                # Fit model
                model.fit(X_train, y_train)

                # Make predictions
                y_pred = model.predict(X_val)

                # Calculate metrics
                fold_metrics = {"fold": fold_idx}

                if problem_type == "regression":
                    fold_metrics["mse"] = float(mean_squared_error(y_val, y_pred))
                    fold_metrics["rmse"] = float(np.sqrt(fold_metrics["mse"]))
                    fold_metrics["mae"] = float(mean_absolute_error(y_val, y_pred))
                    fold_metrics["r2"] = float(r2_score(y_val, y_pred))
                else:  # classification
                    unique_classes = np.unique(y)
                    n_classes = len(unique_classes)

                    fold_metrics["accuracy"] = float(accuracy_score(y_val, y_pred))

                    if n_classes == 2:
                        fold_metrics["precision"] = float(precision_score(y_val, y_pred, zero_division=0))
                        fold_metrics["recall"] = float(recall_score(y_val, y_pred, zero_division=0))
                        fold_metrics["f1"] = float(f1_score(y_val, y_pred, zero_division=0))
                    else:
                        fold_metrics["precision_macro"] = float(
                            precision_score(y_val, y_pred, average="macro", zero_division=0)
                        )
                        fold_metrics["recall_macro"] = float(
                            recall_score(y_val, y_pred, average="macro", zero_division=0)
                        )
                        fold_metrics["f1_macro"] = float(f1_score(y_val, y_pred, average="macro", zero_division=0))

                fold_results.append(fold_metrics)

            except Exception as e:
                logger.exception(f"Error in fold {fold_idx}: {e}")
                fold_results.append(
                    {
                        "fold": fold_idx,
                        "error": str(e),
                    }
                )

        # Create results DataFrame
        results_df = pd.DataFrame(fold_results)

        # Calculate aggregate statistics
        metric_columns = [col for col in results_df.columns if col not in ["fold", "error"]]
        aggregates = {}

        for metric in metric_columns:
            values = results_df[metric].dropna()
            if len(values) > 0:
                aggregates[f"{metric}_mean"] = float(values.mean())
                aggregates[f"{metric}_std"] = float(values.std())
                aggregates[f"{metric}_min"] = float(values.min())
                aggregates[f"{metric}_max"] = float(values.max())

        # Generate summary
        summary = f"📊 {n_folds}-Fold Cross-Validation Results\n\n"
        summary += f"Model: {model_type}\n"
        summary += f"Dataset: {len(df):,} samples, {len(feature_columns)} features\n"
        summary += f"Problem Type: {problem_type.title()}\n"
        summary += (
            f"CV Strategy: {'Stratified' if stratified and problem_type == 'classification' else 'Standard'} K-Fold\n\n"
        )

        summary += "Fold-by-Fold Results:\n"
        summary += results_df.to_string(index=False)
        summary += "\n\n"

        summary += "Aggregate Metrics (Mean ± Std):\n"
        for metric in metric_columns:
            if f"{metric}_mean" in aggregates:
                mean_val = aggregates[f"{metric}_mean"]
                std_val = aggregates[f"{metric}_std"]
                summary += f"  • {metric}: {mean_val:.4f} ± {std_val:.4f}\n"

        # Check for errors
        errors = results_df[results_df["error"].notna()]
        if not errors.empty:
            summary += f"\n⚠️ Errors occurred in {len(errors)} fold(s)\n"

        result_data = {
            "model_type": model_type,
            "problem_type": problem_type,
            "n_folds": n_folds,
            "fold_results": results_df.to_dict(orient="records"),
            "aggregates": aggregates,
            "hyperparameters": hyperparameters,
            "feature_columns": feature_columns,
            "target_column": target_column,
        }

        return ToolResponse(
            payload=result_data,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "model_type": model_type,
                "problem_type": problem_type,
                "n_folds": n_folds,
            },
            storage_hint="session",
            suggested_name=f"cv_{model_type}_{n_folds}fold",
        )

    except Exception as e:
        logger.exception(f"Error in cross-validation: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error in cross-validation: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

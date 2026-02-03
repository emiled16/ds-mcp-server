"""Model training utilities using data_science infrastructure.

Uses sklearn-compatible models with pandas DataFrames.
"""

import os
import re
from typing import Any

import mlflow
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.model_selection import train_test_split


def sanitize_metric_name(name: str) -> str:
    """Sanitize a name for use as MLflow metric/param name.

    MLflow allows: alphanumerics, underscores, dashes, periods, spaces, colons, slashes.
    """
    # Replace parentheses and other invalid chars with underscores
    sanitized = re.sub(r"[^\w\s\-\.:/]", "_", name)
    # Collapse multiple underscores
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized.strip("_")


from src.data_science.regression.models import (
    GradientBoostingRegressorModel,
    LinearRegressionRegressorModel,
    RandomForestRegressorModel,
    XGBRegressorModel,
)

# MLflow configuration - use MLFLOW_SERVER_URL from docker-compose or fallback
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_SERVER_URL", os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
MLFLOW_EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "mcp-ds-agent")

# Map user-friendly names to model classes
MODEL_REGISTRY = {
    "xgboost": XGBRegressorModel,
    "XGBRegressor": XGBRegressorModel,
    "random_forest": RandomForestRegressorModel,
    "RandomForestRegressor": RandomForestRegressorModel,
    "gradient_boosting": GradientBoostingRegressorModel,
    "GradientBoostingRegressor": GradientBoostingRegressorModel,
    "linear": LinearRegressionRegressorModel,
    "LinearRegression": LinearRegressionRegressorModel,
}


async def get_dataset_async(dataset_id: str) -> pd.DataFrame | None:
    """Load dataset from storage by entity_id."""
    from src.storage.repositories.registry import get_repository_registry

    registry = get_repository_registry()
    entity = await registry.get("tool_response", dataset_id)

    if entity and isinstance(entity.payload, pd.DataFrame):
        return entity.payload
    return None


def get_dataset(dataset_id: str) -> pd.DataFrame | None:
    """Load dataset from storage by entity_id (sync wrapper)."""
    import asyncio

    try:
        # Try to get the running loop
        loop = asyncio.get_running_loop()
        # If we're in an async context, create a new thread to run the coroutine
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, get_dataset_async(dataset_id))
            return future.result()
    except RuntimeError:
        # No running loop, we can use asyncio.run directly
        return asyncio.run(get_dataset_async(dataset_id))


def create_model(model_type: str, hyperparameters: dict, input_cols: list, target_col: str):
    """Create a sklearn-compatible model instance."""
    model_class = MODEL_REGISTRY.get(model_type)
    if not model_class:
        raise ValueError(f"Unknown model type: {model_type}. Available: {list(MODEL_REGISTRY.keys())}")

    # Create model config with hyperparameters
    model_config = model_class(**hyperparameters)

    # Get the actual sklearn-compatible model
    return model_config.get_model(
        input_cols=input_cols,
        output_cols=[f"{target_col}_pred"],
        target_cols=[target_col],
    )


def evaluate_model(
    y_true: pd.Series,
    y_pred: np.ndarray,
    prefix: str = "",
) -> dict[str, float]:
    """Evaluate model predictions."""
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    metrics = {
        f"{prefix}rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        f"{prefix}mae": float(mean_absolute_error(y_true, y_pred)),
        f"{prefix}r2": float(r2_score(y_true, y_pred)),
    }
    return metrics


def run_training_with_data(config: dict, df: pd.DataFrame | None) -> dict[str, Any]:
    """Run model training with a pre-loaded DataFrame.

    Args:
        config: Training configuration containing:
            - model_type: Model name (xgboost, random_forest, linear, etc.)
            - target_column: Name of target variable
            - feature_columns: List of feature column names (optional)
            - hyperparameters: Model hyperparameters (optional)
            - test_size: Train/test split ratio (default: 0.2)
            - register_model: Whether to register model in MLflow Model Registry (default: False)
            - model_name: Name for registered model (required if register_model=True)
        df: Pre-loaded DataFrame (avoids async issues)

    Returns:
        Training results including metrics and feature importance
    """
    target_column = config.get("target_column")
    if not target_column:
        return {"status": "error", "message": "Missing required field: target_column"}

    if df is None:
        return {"status": "error", "message": "No DataFrame provided"}

    if target_column not in df.columns:
        return {"status": "error", "message": f"Target column '{target_column}' not in dataset"}

    # Extract config
    model_type = config.get("model_type", "xgboost")
    feature_columns = config.get("feature_columns")
    hyperparameters = config.get("hyperparameters", {})
    test_size = config.get("test_size", 0.2)

    # Determine feature columns
    if not feature_columns:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        feature_columns = [c for c in numeric_cols if c != target_column]

    missing_cols = [c for c in feature_columns if c not in df.columns]
    if missing_cols:
        return {"status": "error", "message": f"Feature columns not found: {missing_cols}"}

    # Prepare data
    X = df[feature_columns].fillna(0)
    y = df[target_column].fillna(df[target_column].mean())

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

    # Create training DataFrames with target column
    train_df = X_train.copy()
    train_df[target_column] = y_train

    test_df = X_test.copy()
    test_df[target_column] = y_test

    # Create and train model
    try:
        model = create_model(model_type, hyperparameters, feature_columns, target_column)
        model.fit(train_df)
    except Exception as e:
        logger.exception(f"Error training model: {e}")
        return {"status": "error", "message": f"Error training model: {e}"}

    # Get predictions
    train_preds = model.predict(train_df)
    test_preds = model.predict(test_df)

    pred_col = f"{target_column}_pred"

    # Evaluate
    train_metrics = evaluate_model(y_train, train_preds[pred_col].values, prefix="train_")
    test_metrics = evaluate_model(y_test, test_preds[pred_col].values, prefix="test_")

    metrics = {**train_metrics, **test_metrics}

    # Feature importance (if available)
    feature_importance = {}
    underlying_model = getattr(model, "_sklearn_object", None) or getattr(model, "to_sklearn", lambda: None)()
    if underlying_model and hasattr(underlying_model, "feature_importances_"):
        for i, col in enumerate(feature_columns):
            feature_importance[col] = float(underlying_model.feature_importances_[i])

    result = {
        "status": "completed",
        "model_type": model_type,
        "metrics": metrics,
        "feature_importance": feature_importance,
        "dataset_shape": {"rows": len(df), "features": len(feature_columns)},
        "train_size": len(X_train),
        "test_size": len(X_test),
        "config": config,
    }

    # Log to MLflow
    run_id = None
    model_version = None
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

        with mlflow.start_run(run_name=f"{model_type}_{target_column}") as run:
            run_id = run.info.run_id

            # Log parameters
            mlflow.log_param("model_type", model_type)
            mlflow.log_param("target_column", target_column)
            mlflow.log_param("feature_columns", feature_columns)
            mlflow.log_param("test_size", test_size)
            for k, v in hyperparameters.items():
                mlflow.log_param(f"hp_{k}", v)

            # Log metrics
            for metric_name, metric_value in metrics.items():
                mlflow.log_metric(metric_name, metric_value)

            # Log feature importance (sanitize names for MLflow)
            if feature_importance:
                for feat, imp in feature_importance.items():
                    safe_name = sanitize_metric_name(f"importance_{feat}")
                    mlflow.log_metric(safe_name, imp)

            # Log model
            mlflow.sklearn.log_model(underlying_model, "model")

            logger.info(f"Logged to MLflow: run_id={run_id}")
            result["mlflow_run_id"] = run_id

            # Register model if requested
            register_model = config.get("register_model", False)
            model_name = config.get("model_name")

            if register_model:
                if not model_name:
                    logger.warning("register_model=True but model_name not provided. Skipping registration.")
                    result["registration_warning"] = "model_name required for registration"
                else:
                    try:
                        model_uri = f"runs:/{run_id}/model"
                        registered_model = mlflow.register_model(model_uri, model_name)
                        model_version = registered_model.version
                        logger.info(f"Registered model '{model_name}' version {model_version}")
                        result["registered_model_name"] = model_name
                        result["registered_model_version"] = model_version
                    except Exception as reg_err:
                        logger.exception(f"Failed to register model: {reg_err}")
                        result["registration_error"] = str(reg_err)

    except Exception as e:
        logger.warning(f"Failed to log to MLflow: {e}")

    logger.info(f"Training completed: {metrics}")
    return result


def run_training(config: dict) -> dict[str, Any]:
    """Run model training (loads dataset from storage).

    For Celery async tasks. For sync execution in async context,
    use run_training_with_data() with pre-loaded DataFrame.
    """
    dataset_id = config.get("dataset_id")
    if not dataset_id:
        return {"status": "error", "message": "Missing required field: dataset_id"}

    df = get_dataset(dataset_id)
    if df is None:
        return {"status": "error", "message": f"Dataset not found: {dataset_id}"}

    return run_training_with_data(config, df)

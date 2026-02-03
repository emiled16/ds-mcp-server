"""Hyperparameter tuning implementation for MCP agent.

Simplified HPT using Optuna with MLflow logging.
"""

import os
from typing import Any

import mlflow
import numpy as np
import optuna
import pandas as pd
from loguru import logger
from optuna import Trial
from sklearn.model_selection import train_test_split

from src.workers.training import MODEL_REGISTRY, create_model, evaluate_model, sanitize_metric_name


def create_optuna_suggest_from_space(trial: Trial, param_space: dict[str, Any]) -> dict[str, Any]:
    """Convert param_space dict to Optuna trial suggestions.

    Param space format:
    {
        "n_estimators": {"type": "int", "low": 50, "high": 500},
        "max_depth": {"type": "int", "low": 3, "high": 15},
        "learning_rate": {"type": "float", "low": 0.01, "high": 0.3, "log": True},
        "subsample": {"type": "categorical", "choices": [0.6, 0.8, 1.0]},
    }
    """
    params = {}
    for name, spec in param_space.items():
        param_type = spec.get("type", "categorical")

        if param_type == "int":
            params[name] = trial.suggest_int(
                name, spec["low"], spec["high"], step=spec.get("step", 1), log=spec.get("log", False)
            )
        elif param_type == "float":
            params[name] = trial.suggest_float(
                name, spec["low"], spec["high"], step=spec.get("step"), log=spec.get("log", False)
            )
        elif param_type == "categorical":
            params[name] = trial.suggest_categorical(name, spec["choices"])
        else:
            logger.warning(f"Unknown param type {param_type} for {name}, using categorical")
            params[name] = trial.suggest_categorical(name, [spec.get("default", spec)])

    return params


def run_hpt_trial(
    trial: Trial,
    df: pd.DataFrame,
    model_type: str,
    target_column: str,
    feature_columns: list[str],
    param_space: dict[str, Any],
    test_size: float,
    metric_to_optimize: str = "test_rmse",
) -> float:
    """Run a single HPT trial.

    Returns the metric value to optimize (lower is better for rmse).
    """
    # Suggest hyperparameters
    hyperparams = create_optuna_suggest_from_space(trial, param_space)

    # Prepare data - models expect DataFrame with all columns
    train_df, test_df = train_test_split(df, test_size=test_size, random_state=42)

    # Create and train model (sklearn wrapper - pass DataFrame)
    model = create_model(model_type, hyperparams, feature_columns, target_column)
    model.fit(train_df)

    # Predictions
    train_pred_df = model.predict(train_df)
    test_pred_df = model.predict(test_df)

    # Extract actual and predicted values
    pred_col = f"{target_column}_pred"
    y_train = train_df[target_column].values
    y_test = test_df[target_column].values
    y_train_pred = train_pred_df[pred_col].values
    y_test_pred = test_pred_df[pred_col].values

    # Evaluate (call separately for train and test)
    train_metrics = evaluate_model(y_train, y_train_pred, prefix="train_")
    test_metrics = evaluate_model(y_test, y_test_pred, prefix="test_")
    metrics = {**train_metrics, **test_metrics}

    # Log trial to MLflow
    with mlflow.start_run(nested=True, run_name=f"trial_{trial.number}"):
        mlflow.log_params(hyperparams)
        mlflow.log_params({"trial_number": trial.number})
        for metric_name, value in metrics.items():
            safe_name = sanitize_metric_name(metric_name)
            mlflow.log_metric(safe_name, value)

    # Return metric to optimize
    return metrics.get(metric_to_optimize, metrics.get("test_rmse", float("inf")))


def run_hyperparameter_tuning(config: dict) -> dict:
    """Run hyperparameter tuning with Optuna.

    Args:
        config: Configuration dictionary containing:
            - dataset_id: Entity ID of the dataset
            - model_type: Model type (xgboost, random_forest, etc.)
            - target_column: Name of target variable
            - feature_columns: List of feature column names
            - param_space: Dict defining search space per hyperparameter
            - n_trials: Number of Optuna trials (default: 20)
            - test_size: Train/test split ratio (default: 0.2)
            - metric_to_optimize: Metric name (default: "test_rmse")
            - direction: "minimize" or "maximize" (default: "minimize")

    Returns:
        Dictionary with best params, metrics, and study info
    """
    from src.workers.training import get_dataset

    # Extract config
    dataset_id = config.get("dataset_id")
    model_type = config.get("model_type", "xgboost")
    target_column = config["target_column"]
    feature_columns = config.get("feature_columns")
    param_space = config.get("param_space", {})
    n_trials = config.get("n_trials", 20)
    test_size = config.get("test_size", 0.2)
    metric_to_optimize = config.get("metric_to_optimize", "test_rmse")
    direction = config.get("direction", "minimize")

    # Validate model type
    if model_type not in MODEL_REGISTRY:
        raise ValueError(f"Unknown model type: {model_type}. Available: {list(MODEL_REGISTRY.keys())}")

    # Load dataset (use pre-loaded DataFrame if available)
    df = config.pop("_dataframe", None)
    if df is None:
        logger.info(f"Loading dataset {dataset_id}...")
        df = get_dataset(dataset_id)
    else:
        logger.info("Using pre-loaded DataFrame")

    # Auto-detect feature columns if not provided
    if feature_columns is None:
        feature_columns = [col for col in df.select_dtypes(include=[np.number]).columns if col != target_column]
        logger.info(f"Auto-detected feature columns: {feature_columns}")

    # Validate columns exist
    missing = set(feature_columns + [target_column]) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Clean data
    df_clean = df[feature_columns + [target_column]].dropna()
    logger.info(f"Dataset shape after cleaning: {df_clean.shape}")

    # Setup MLflow
    mlflow_tracking_uri = os.getenv("MLFLOW_SERVER_URL", "http://localhost:5000")
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment("mcp-ds-agent-hpt")

    # Create parent run for the study
    with mlflow.start_run(run_name=f"hpt_{model_type}_{target_column}") as parent_run:
        mlflow.log_params(
            {
                "model_type": model_type,
                "target_column": target_column,
                "n_trials": n_trials,
                "n_features": len(feature_columns),
                "dataset_rows": len(df_clean),
                "metric_to_optimize": metric_to_optimize,
            }
        )

        # Create Optuna study
        study = optuna.create_study(
            direction=direction,
            study_name=f"hpt_{model_type}",
        )

        # Define objective
        def objective(trial: Trial) -> float:
            return run_hpt_trial(
                trial=trial,
                df=df_clean,
                model_type=model_type,
                target_column=target_column,
                feature_columns=feature_columns,
                param_space=param_space,
                test_size=test_size,
                metric_to_optimize=metric_to_optimize,
            )

        # Run optimization
        logger.info(f"Starting Optuna optimization with {n_trials} trials...")
        study.optimize(objective, n_trials=n_trials, n_jobs=1, show_progress_bar=False)

        # Log best results to parent run
        mlflow.log_params({f"best_{k}": v for k, v in study.best_params.items()})
        mlflow.log_metric(f"best_{metric_to_optimize}", study.best_value)

        # Get all trial results
        trials_df = study.trials_dataframe()

        logger.info(f"HPT completed: best {metric_to_optimize}={study.best_value:.4f}")
        logger.info(f"Best params: {study.best_params}")

    return {
        "status": "completed",
        "model_type": model_type,
        "n_trials": n_trials,
        "best_params": study.best_params,
        "best_value": study.best_value,
        "metric_to_optimize": metric_to_optimize,
        "direction": direction,
        "mlflow_run_id": parent_run.info.run_id,
        "all_trials": [
            {
                "number": t.number,
                "value": t.value,
                "params": t.params,
                "state": str(t.state),
            }
            for t in study.trials[:10]  # First 10 trials summary
        ],
        "dataset_shape": {"rows": len(df_clean), "features": len(feature_columns)},
        "config": config,
    }

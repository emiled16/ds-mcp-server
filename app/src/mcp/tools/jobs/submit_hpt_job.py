"""Submit hyperparameter tuning job tool."""

import pandas as pd

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.job import Job, JobStatus
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry
from src.workers.celery_app import app as celery_app


@mcp.tool
@process_tool
@register_tool
async def submit_hpt_job(
    config: dict,
    async_mode: bool = True,
) -> str:
    """Submit a hyperparameter tuning job.

    Runs Optuna-based hyperparameter search with MLflow logging.

    Args:
        config: HPT configuration dictionary containing:
            - dataset_id: Entity ID of the dataset (required)
            - model_type: Model type (xgboost, random_forest, gradient_boosting, linear)
            - target_column: Name of target variable (required)
            - feature_columns: List of feature column names (optional, auto-detected)
            - param_space: Dict defining search space (required), format:
                {
                    "n_estimators": {"type": "int", "low": 50, "high": 500},
                    "max_depth": {"type": "int", "low": 3, "high": 15},
                    "learning_rate": {"type": "float", "low": 0.01, "high": 0.3, "log": True},
                    "subsample": {"type": "categorical", "choices": [0.6, 0.8, 1.0]},
                }
            - n_trials: Number of trials (default: 20)
            - metric_to_optimize: Metric name (default: "test_rmse")
            - direction: "minimize" or "maximize" (default: "minimize")
        async_mode: If True, submit to Celery; if False, run synchronously

    Returns:
        ToolResponse with job ID (async) or HPT results (sync)

    Example:
        "Tune XGBoost hyperparameters"
        → submit_hpt_job(config={
            "dataset_id": "abc123",
            "model_type": "xgboost",
            "target_column": "price",
            "param_space": {
                "n_estimators": {"type": "int", "low": 50, "high": 200},
                "max_depth": {"type": "int", "low": 3, "high": 10},
            },
            "n_trials": 20
        })
    """
    # Validate config
    required_fields = ["model_type", "target_column", "param_space"]
    missing = [f for f in required_fields if f not in config]
    if missing:
        return ToolResponse(
            payload=None,
            summary=f"Error: Missing required config fields: {missing}",
            metadata={"error": "ValidationError", "missing_fields": missing},
            storage_hint="never",
        )

    if async_mode:
        try:
            # Submit to Celery
            task = celery_app.send_task(
                "tasks.run_hyperparameter_tuning",
                args=[config],
            )

            # Create job record
            job = Job(
                celery_task_id=task.id,
                task_name="run_hyperparameter_tuning",
                kwargs={"config": config},
                status=JobStatus.PENDING,
                metadata={
                    "model_type": config.get("model_type"),
                    "target_column": config.get("target_column"),
                    "n_trials": config.get("n_trials", 20),
                },
            )

            # Save job
            registry = get_repository_registry()
            job_repo = registry.get_repository("job")
            await job_repo.save(job)

            summary = (
                f"HPT job submitted successfully!\n\n"
                f"Job ID: {job.entity_id}\n"
                f"Task ID: {task.id}\n"
                f"Status: PENDING\n"
                f"Model Type: {config.get('model_type', 'unknown')}\n"
                f"Trials: {config.get('n_trials', 20)}\n\n"
                f"Use get_job_status(job_id='{job.entity_id}') to check progress.\n"
                f"Use get_job_result(job_id='{job.entity_id}') when complete."
            )

            return ToolResponse(
                payload={
                    "job_id": job.entity_id,
                    "celery_task_id": task.id,
                    "status": "PENDING",
                    "async": True,
                },
                summary=summary,
                metadata={
                    "job_id": job.entity_id,
                    "model_type": config.get("model_type"),
                    "n_trials": config.get("n_trials", 20),
                    "async": True,
                },
                storage_hint="always",
                suggested_name=f"hpt_job_{config.get('model_type', 'model')}",
            )

        except Exception as e:
            return ToolResponse(
                payload=None,
                summary=f"Error submitting HPT job: {e}",
                metadata={"error": type(e).__name__, "details": str(e)},
                storage_hint="never",
            )

    else:
        # Synchronous execution
        try:
            from src.workers.hyperparameter_tuning import run_hyperparameter_tuning

            # Load dataset if dataset_id provided
            dataset_id = config.get("dataset_id")
            if dataset_id:
                registry = get_repository_registry()
                entity = await registry.get("tool_response", dataset_id)
                if entity and isinstance(entity.payload, pd.DataFrame):
                    # Store DataFrame in config for HPT to use
                    config["_dataframe"] = entity.payload
                else:
                    return ToolResponse(
                        payload=None,
                        summary=f"Error: Dataset '{dataset_id}' not found or invalid",
                        metadata={"error": "NotFound", "dataset_id": dataset_id},
                        storage_hint="never",
                    )

            # Run HPT synchronously
            result = run_hyperparameter_tuning(config)

            summary = (
                f"HPT completed!\n\n"
                f"Model Type: {config.get('model_type', 'unknown')}\n"
                f"Trials: {result.get('n_trials', 'unknown')}\n"
                f"Best {result.get('metric_to_optimize', 'metric')}: "
                f"{result.get('best_value', 'N/A'):.4f}\n\n"
                f"Best Parameters:\n"
            )

            if "best_params" in result:
                for param, value in result["best_params"].items():
                    summary += f"  • {param}: {value}\n"

            if "mlflow_run_id" in result:
                summary += f"\nMLflow Run ID: {result['mlflow_run_id']}"

            return ToolResponse(
                payload=result,
                summary=summary,
                metadata={
                    "model_type": config.get("model_type"),
                    "n_trials": result.get("n_trials"),
                    "best_value": result.get("best_value"),
                    "async": False,
                },
                storage_hint="session",
                suggested_name=f"hpt_result_{config.get('model_type', 'model')}",
            )

        except Exception as e:
            return ToolResponse(
                payload=None,
                summary=f"Error during HPT: {e}",
                metadata={"error": type(e).__name__, "details": str(e)},
                storage_hint="never",
            )

"""Submit training job tool."""

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
async def submit_training_job(
    config: dict,
    async_mode: bool = True,
) -> str:
    """Submit a model training job.

    Submits a model training configuration to the task queue for async execution,
    or runs it synchronously if async_mode=False.

    Args:
        config: Training configuration dictionary containing:
            - model_type: Type of model to train (e.g., 'xgboost', 'lightgbm')
            - target_column: Name of target variable
            - feature_columns: List of feature column names
            - hyperparameters: Model hyperparameters
            - Additional config fields as needed
        async_mode: If True, submit to queue; if False, run synchronously

    Returns:
        ToolResponse with job ID (async) or training results (sync)

    Example:
        "Train an XGBoost model on the sales data"
        → submit_training_job(config={
            "model_type": "xgboost",
            "target_column": "sales",
            "feature_columns": ["price", "quantity", "category"],
            "hyperparameters": {"n_estimators": 100, "max_depth": 5}
        })
    """
    # Validate config
    required_fields = ["model_type"]
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
                "tasks.train_model",
                args=[config],
            )

            # Create job record
            job = Job(
                celery_task_id=task.id,
                task_name="train_model",
                kwargs={"config": config},
                status=JobStatus.PENDING,
                metadata={
                    "model_type": config.get("model_type"),
                    "target_column": config.get("target_column"),
                },
            )

            # Save job
            registry = get_repository_registry()
            job_repo = registry.get_repository("job")
            await job_repo.save(job)

            summary = (
                f"Training job submitted successfully!\n\n"
                f"Job ID: {job.entity_id}\n"
                f"Task ID: {task.id}\n"
                f"Status: PENDING\n"
                f"Model Type: {config.get('model_type', 'unknown')}\n\n"
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
                    "async": True,
                },
                storage_hint="always",
                suggested_name=f"training_job_{config.get('model_type', 'model')}",
            )

        except Exception as e:
            return ToolResponse(
                payload=None,
                summary=f"Error submitting training job: {e}",
                metadata={"error": type(e).__name__, "details": str(e)},
                storage_hint="never",
            )

    else:
        # Synchronous execution - load dataset first since we're in async context
        try:
            import pandas as pd

            from src.workers.training import run_training_with_data

            # Load dataset if dataset_id provided
            dataset_id = config.get("dataset_id")
            df = None
            if dataset_id:
                registry = get_repository_registry()
                entity = await registry.get("tool_response", dataset_id)
                if entity and isinstance(entity.payload, pd.DataFrame):
                    df = entity.payload
                else:
                    return ToolResponse(
                        payload=None,
                        summary=f"Error: Dataset '{dataset_id}' not found or invalid",
                        metadata={"error": "NotFound", "dataset_id": dataset_id},
                        storage_hint="never",
                    )

            # Run training with DataFrame directly
            result = run_training_with_data(config, df)

            summary = (
                f"Training completed synchronously.\n\n"
                f"Model Type: {config.get('model_type', 'unknown')}\n"
                f"Status: {result.get('status', 'unknown')}\n"
            )

            if "metrics" in result:
                summary += "\nMetrics:\n"
                for metric, value in result["metrics"].items():
                    summary += f"  • {metric}: {value:.4f}\n"

            if result.get("feature_importance"):
                summary += "\nFeature Importance:\n"
                sorted_importance = sorted(result["feature_importance"].items(), key=lambda x: x[1], reverse=True)
                for feat, imp in sorted_importance[:5]:
                    summary += f"  • {feat}: {imp:.4f}\n"

            return ToolResponse(
                payload=result,
                summary=summary,
                metadata={
                    "model_type": config.get("model_type"),
                    "async": False,
                },
                storage_hint="session",
                suggested_name=f"training_result_{config.get('model_type', 'model')}",
            )

        except Exception as e:
            return ToolResponse(
                payload=None,
                summary=f"Error during synchronous training: {e}",
                metadata={"error": type(e).__name__, "details": str(e)},
                storage_hint="never",
            )

"""Celery task definitions for async job execution.

Tasks defined here can be submitted to Celery workers for background processing.
Long-running operations like model training should use these tasks.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any

import psycopg2
from celery import Task
from loguru import logger

from src.models.job import JobStatus
from src.workers.celery_app import app


def _sync_update_job_status(
    task_id: str,
    status: JobStatus,
    result: Any = None,
    error: str | None = None,
) -> None:
    """Update job status in Postgres (app.documents) using synchronous psycopg2.

    Uses psycopg2 directly to avoid event loop issues in Celery callbacks.
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            dbname=os.getenv("POSTGRES_DB", "maxa_ds"),
            user=os.getenv("POSTGRES_USER", "appuser"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            connect_timeout=5,
        )
        conn.autocommit = False
        schema = os.getenv("POSTGRES_SCHEMA", "app")

        update_data = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if result is not None:
            update_data["result"] = result
        if error is not None:
            update_data["error"] = error
        if status in (JobStatus.SUCCESS, JobStatus.FAILURE):
            update_data["completed_at"] = datetime.now(timezone.utc).isoformat()

        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE "{schema}".documents
                SET data = data || %s::jsonb
                WHERE collection = 'jobs' AND data->>'celery_task_id' = %s
                """,
                (json.dumps(update_data, default=str), task_id),
            )
            if cur.rowcount > 0:
                logger.info(f"Updated job status to {status.value} for task {task_id}")
            else:
                logger.warning(f"No job found for task_id {task_id}")
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to update job status for task {task_id}: {e}")


class CallbackTask(Task):
    """Base task with lifecycle callbacks for logging and monitoring."""

    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict) -> None:
        """Called when task completes successfully."""
        logger.info(f"Task {task_id} succeeded")
        _sync_update_job_status(task_id, JobStatus.SUCCESS, result=retval)

    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any,
    ) -> None:
        """Called when task fails."""
        logger.error(f"Task {task_id} failed: {exc}")
        _sync_update_job_status(task_id, JobStatus.FAILURE, error=str(exc))

    def on_retry(
        self,
        exc: Exception,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any,
    ) -> None:
        """Called when task is retried."""
        logger.warning(f"Task {task_id} retrying: {exc}")
        _sync_update_job_status(task_id, JobStatus.RETRY)


@app.task(base=CallbackTask, bind=True, name="tasks.run_tool")
def run_tool(self: Task, func_name: str, args: tuple, kwargs: dict) -> Any:
    """Execute a tool asynchronously.

    Args:
        self: Celery task instance (bound)
        func_name: Name of the tool function to execute
        args: Positional arguments for the tool
        kwargs: Keyword arguments for the tool

    Returns:
        Tool execution result
    """
    logger.info(f"Running tool {func_name} with args={args}, kwargs={kwargs}")

    # Import tool function dynamically
    from src.mcp.tools import get_tool_function

    tool_func = get_tool_function(func_name)
    if tool_func is None:
        raise ValueError(f"Tool function not found: {func_name}")

    # Execute async tool in sync context
    result = asyncio.run(tool_func(*args, **kwargs))

    return result


@app.task(base=CallbackTask, bind=True, name="tasks.train_model")
def train_model(self: Task, config: dict) -> dict:
    """Train a model using Snowflake ML (works locally with pandas).

    Args:
        self: Celery task instance (bound)
        config: Training configuration dictionary containing:
            - dataset_id: Entity ID of the dataset
            - model_type: Model type (xgboost, random_forest, gradient_boosting, linear)
            - target_column: Name of target variable
            - feature_columns: List of feature column names (optional)
            - hyperparameters: Model hyperparameters (optional)
            - test_size: Train/test split ratio (default: 0.2)

    Returns:
        Training results including metrics and feature importance
    """
    from src.workers.training import run_training

    logger.info(f"Training model with config: {config}")
    return run_training(config)


@app.task(base=CallbackTask, bind=True, name="tasks.run_hyperparameter_tuning")
def run_hyperparameter_tuning(self: Task, config: dict) -> dict:
    """Run hyperparameter tuning asynchronously.

    Args:
        self: Celery task instance (bound)
        config: Configuration dictionary containing:
            - dataset_id: Entity ID of the dataset
            - model_type: Model type (xgboost, random_forest, etc.)
            - target_column: Name of target variable
            - feature_columns: List of feature column names (optional)
            - param_space: Dict defining search space per hyperparameter
            - n_trials: Number of trials (default: 20)
            - test_size: Train/test split ratio (default: 0.2)
            - metric_to_optimize: Metric name (default: "test_rmse")
            - direction: "minimize" or "maximize" (default: "minimize")

    Returns:
        Tuning results including best parameters and metrics
    """
    from src.workers.hyperparameter_tuning import run_hyperparameter_tuning

    logger.info(f"Running HPT with config: {config}")
    return run_hyperparameter_tuning(config)

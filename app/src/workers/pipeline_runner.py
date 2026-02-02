"""Pipeline runner for orchestrating multi-step ML workflows."""

import os
from datetime import datetime

import mlflow
from loguru import logger

from src.models.pipeline import Pipeline, PipelineStatus, PipelineStepStatus, PipelineStepType
from src.workers.hyperparameter_tuning import run_hyperparameter_tuning
from src.workers.training import run_training

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_SERVER_URL", os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
MLFLOW_EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "mcp-ds-agent")


def run_pipeline(pipeline: Pipeline) -> Pipeline:
    """Run a complete ML pipeline.

    Executes all steps in sequence:
    1. Feature engineering (if present)
    2. Model training
    3. Hyperparameter tuning (if present)

    Args:
        pipeline: Pipeline configuration with steps

    Returns:
        Updated pipeline with results
    """
    logger.info(f"Starting pipeline execution: {pipeline.name}")
    logger.info(f"Pipeline has {len(pipeline.steps)} steps")

    # Update pipeline status
    pipeline.status = PipelineStatus.RUNNING
    pipeline.started_at = datetime.now()

    # Start MLflow parent run
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    try:
        with mlflow.start_run(run_name=f"pipeline_{pipeline.name}") as parent_run:
            pipeline.mlflow_parent_run_id = parent_run.info.run_id

            # Log pipeline metadata
            mlflow.log_param("pipeline_name", pipeline.name)
            mlflow.log_param("pipeline_id", pipeline.entity_id)
            mlflow.log_param("num_steps", len(pipeline.steps))

            # Track data flow between steps
            current_dataset_id = None
            feature_pipeline_run_id = None

            # Execute steps in order
            for i, step in enumerate(pipeline.steps):
                logger.info(f"Executing step {i + 1}/{len(pipeline.steps)}: {step.type}")

                step.status = PipelineStepStatus.RUNNING
                step.started_at = datetime.now()

                try:
                    # Execute based on step type
                    if step.type == PipelineStepType.FEATURE_PIPELINE:
                        result = _run_feature_pipeline_step(step, current_dataset_id)
                        if result.get("transformed_dataset_id"):
                            current_dataset_id = result["transformed_dataset_id"]
                        if result.get("mlflow_run_id"):
                            feature_pipeline_run_id = result["mlflow_run_id"]

                    elif step.type == PipelineStepType.TRAINING:
                        # Use transformed dataset if available
                        if current_dataset_id:
                            step.config["dataset_id"] = current_dataset_id
                        result = _run_training_step(step)

                    elif step.type == PipelineStepType.HPT:
                        # Use transformed dataset if available
                        if current_dataset_id:
                            step.config["dataset_id"] = current_dataset_id
                        result = _run_hpt_step(step)

                    else:
                        raise ValueError(f"Unknown step type: {step.type}")

                    # Update step with results
                    step.result = result
                    step.status = PipelineStepStatus.COMPLETED
                    step.completed_at = datetime.now()

                    logger.info(f"Step {i + 1} completed successfully")

                except Exception as e:
                    logger.exception(f"Error in step {i + 1}: {e}")
                    step.status = PipelineStepStatus.FAILED
                    step.error = str(e)
                    step.completed_at = datetime.now()

                    # Mark pipeline as failed
                    pipeline.status = PipelineStatus.FAILED
                    pipeline.completed_at = datetime.now()

                    mlflow.log_param(f"step_{i}_status", "failed")
                    mlflow.log_param(f"step_{i}_error", str(e))

                    return pipeline

                # Log step completion to MLflow
                mlflow.log_param(f"step_{i}_type", step.type)
                mlflow.log_param(f"step_{i}_status", "completed")

            # All steps completed successfully
            pipeline.status = PipelineStatus.COMPLETED
            pipeline.completed_at = datetime.now()

            logger.info(f"Pipeline '{pipeline.name}' completed successfully")

    except Exception as e:
        logger.exception(f"Error in pipeline execution: {e}")
        pipeline.status = PipelineStatus.FAILED
        pipeline.completed_at = datetime.now()

    return pipeline


def _run_feature_pipeline_step(step, dataset_id: str | None) -> dict:
    """Run a feature pipeline step.

    This is a placeholder - in practice, this would call the feature pipeline
    creation logic. For now, we'll just pass through.
    """
    from src.data_science.feature_store.pipeline import FeaturePipeline

    # Extract config
    pipeline_config = step.config.get("pipeline_config", {})
    input_dataset_id = step.config.get("dataset_id") or dataset_id

    if not input_dataset_id:
        raise ValueError("Feature pipeline step requires dataset_id")

    # Create and fit pipeline (simplified - in real implementation, would load dataset)
    steps_config = pipeline_config.get("steps", [])
    pipeline = FeaturePipeline(steps=steps_config)

    # Note: Actual fitting would happen here with real data
    # For now, return metadata
    return {
        "status": "completed",
        "num_steps": len(steps_config),
        "dataset_id": input_dataset_id,
        "transformed_dataset_id": input_dataset_id,  # In real impl, this would be new ID
    }


def _run_training_step(step) -> dict:
    """Run a training step."""
    config = step.config
    result = run_training(config)
    return result


def _run_hpt_step(step) -> dict:
    """Run a hyperparameter tuning step."""
    config = step.config
    result = run_hyperparameter_tuning(config)
    return result

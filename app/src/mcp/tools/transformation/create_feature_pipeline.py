"""Create and save a feature engineering pipeline."""

import os
import tempfile

import mlflow
import pandas as pd
from loguru import logger

from src.data_science.feature_store.pipeline import FeaturePipeline
from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_SERVER_URL", os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
MLFLOW_EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "mcp-ds-agent")


@mcp.tool
@process_tool
@register_tool
async def create_feature_pipeline(
    dataset_id: str,
    pipeline_config: dict,
    pipeline_name: str,
    save_transformed_data: bool = True,
) -> str:
    """Create, fit, and save a feature engineering pipeline.

    Creates a reusable feature pipeline by chaining transformations,
    fits it on the training data, and saves it to MLflow as a PyFunc model.

    Args:
        dataset_id: Entity ID of the dataset to fit the pipeline on
        pipeline_config: Pipeline configuration with list of transformation steps:
            {
                "steps": [
                    {
                        "name": "FillColsValues",
                        "parameters": {"fill_values": {"price": 0}}
                    },
                    {
                        "name": "ScalingNumerical",
                        "parameters": {"columns": ["price", "quantity"], "method": "standard"}
                    }
                ]
            }
        pipeline_name: Name for the pipeline (used in MLflow)
        save_transformed_data: Whether to save the transformed dataset (default: True)

    Returns:
        ToolResponse with pipeline info and transformed data (if saved)

    Example:
        "Create a feature pipeline with scaling and lag features"
        → create_feature_pipeline(
            dataset_id="abc123",
            pipeline_config={
                "steps": [
                    {
                        "name": "ScalingNumerical",
                        "parameters": {"columns": ["price"], "method": "standard"}
                    },
                    {
                        "name": "Lag",
                        "parameters": {
                            "lags": {"sales": [1, 7]},
                            "columns_to_order_by": ["date"]
                        }
                    }
                ]
            },
            pipeline_name="sales_preprocessing_v1"
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

        # Validate pipeline config
        steps = pipeline_config.get("steps", [])
        if not steps:
            return ToolResponse(
                payload=None,
                summary="Error: Pipeline config must include 'steps' list",
                metadata={"error": "ValidationError"},
                storage_hint="never",
            )

        # Create and fit pipeline
        logger.info(f"Creating feature pipeline '{pipeline_name}' with {len(steps)} steps")
        pipeline = FeaturePipeline(steps=steps)

        original_shape = df.shape
        try:
            transformed_df = pipeline.fit_transform(df)
        except Exception as e:
            logger.exception(f"Error fitting pipeline: {e}")
            return ToolResponse(
                payload=None,
                summary=f"Error fitting pipeline: {e}",
                metadata={"error": "PipelineFitError", "details": str(e)},
                storage_hint="never",
            )

        # Save pipeline to MLflow
        mlflow_run_id = None
        mlflow_model_uri = None

        try:
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

            with mlflow.start_run(run_name=f"feature_pipeline_{pipeline_name}") as run:
                mlflow_run_id = run.info.run_id

                # Log pipeline config
                mlflow.log_param("pipeline_name", pipeline_name)
                mlflow.log_param("num_steps", len(steps))
                for i, step in enumerate(steps):
                    mlflow.log_param(f"step_{i}_name", step.get("name"))

                # Log data shapes
                mlflow.log_metric("original_rows", original_shape[0])
                mlflow.log_metric("original_cols", original_shape[1])
                mlflow.log_metric("transformed_rows", transformed_df.shape[0])
                mlflow.log_metric("transformed_cols", transformed_df.shape[1])

                # Save pipeline as MLflow model
                with tempfile.TemporaryDirectory() as tmpdir:
                    mlflow.pyfunc.log_model(
                        artifact_path="pipeline",
                        python_model=pipeline,
                        conda_env={
                            "channels": ["defaults"],
                            "dependencies": [
                                f"python={os.sys.version_info.major}.{os.sys.version_info.minor}",
                                "pip",
                                {
                                    "pip": [
                                        "pandas",
                                        "scikit-learn",
                                        "mlflow",
                                    ]
                                },
                            ],
                            "name": "feature_pipeline_env",
                        },
                    )

                mlflow_model_uri = f"runs:/{mlflow_run_id}/pipeline"
                logger.info(f"Saved pipeline to MLflow: {mlflow_model_uri}")

        except Exception as e:
            logger.exception(f"Error saving pipeline to MLflow: {e}")
            return ToolResponse(
                payload=None,
                summary=f"Pipeline fitted but failed to save to MLflow: {e}",
                metadata={"error": "MLflowSaveError", "details": str(e)},
                storage_hint="never",
            )

        # Prepare result
        result = {
            "pipeline_name": pipeline_name,
            "num_steps": len(steps),
            "steps": steps,
            "original_shape": original_shape,
            "transformed_shape": transformed_df.shape,
            "mlflow_run_id": mlflow_run_id,
            "mlflow_model_uri": mlflow_model_uri,
        }

        summary = "✅ Feature pipeline created successfully!\n\n"
        summary += f"Pipeline: {pipeline_name}\n"
        summary += f"Steps: {len(steps)}\n"
        summary += f"MLflow Run ID: {mlflow_run_id}\n"
        summary += f"Model URI: {mlflow_model_uri}\n\n"
        summary += "Data Transformation:\n"
        summary += f"  Original: {original_shape[0]:,} rows × {original_shape[1]} columns\n"
        summary += f"  Transformed: {transformed_df.shape[0]:,} rows × {transformed_df.shape[1]} columns\n\n"

        step_summary = "Pipeline Steps:\n"
        for i, step in enumerate(steps):
            step_summary += f"  {i + 1}. {step.get('name')}\n"
        summary += step_summary

        # Save transformed dataset if requested
        transformed_entity_id = None
        if save_transformed_data:
            try:
                transformed_response = ToolResponse(
                    payload=transformed_df,
                    summary=f"Transformed data from pipeline '{pipeline_name}'",
                    metadata={
                        "pipeline_name": pipeline_name,
                        "mlflow_run_id": mlflow_run_id,
                        "original_dataset_id": dataset_id,
                    },
                    storage_hint="session",
                    suggested_name=f"{entity.suggested_name or 'data'}_{pipeline_name}",
                )

                tool_response_repo = registry.get_repository("tool_response")
                await tool_response_repo.save(transformed_response)
                transformed_entity_id = transformed_response.entity_id

                result["transformed_dataset_id"] = transformed_entity_id
                summary += f"\n📊 Transformed dataset saved: {transformed_entity_id}"

            except Exception as e:
                logger.warning(f"Failed to save transformed dataset: {e}")

        summary += "\n\nTo use this pipeline:\n"
        summary += f"  • Load: load_feature_pipeline(run_id='{mlflow_run_id}')\n"
        summary += f"  • Apply: run_feature_pipeline(dataset_id=..., pipeline_run_id='{mlflow_run_id}')"

        return ToolResponse(
            payload=result,
            summary=summary,
            metadata={
                "pipeline_name": pipeline_name,
                "mlflow_run_id": mlflow_run_id,
                "transformed_dataset_id": transformed_entity_id,
            },
            storage_hint="session",
            suggested_name=f"pipeline_{pipeline_name}",
        )

    except Exception as e:
        logger.exception(f"Error creating feature pipeline: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error creating feature pipeline: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

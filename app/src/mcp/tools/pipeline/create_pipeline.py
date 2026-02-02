"""Create a multi-step ML pipeline."""

from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.pipeline import Pipeline, PipelineStep, PipelineStepType
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def create_pipeline(
    name: str,
    steps_config: list[dict],
    description: str | None = None,
) -> str:
    """Create a multi-step ML pipeline.

    Creates a pipeline that chains together feature engineering, training,
    and hyperparameter tuning steps. The pipeline can be executed with
    run_pipeline().

    Args:
        name: Name for the pipeline
        steps_config: List of step configurations, each with:
            {
                "type": "feature_pipeline" | "training" | "hpt",
                "config": {...}  # Step-specific configuration
            }
        description: Optional description

    Returns:
        ToolResponse with pipeline configuration

    Example:
        "Create a pipeline with feature engineering and training"
        → create_pipeline(
            name="sales_prediction_v1",
            steps_config=[
                {
                    "type": "feature_pipeline",
                    "config": {
                        "dataset_id": "abc123",
                        "pipeline_config": {
                            "steps": [
                                {"name": "ScalingNumerical", "parameters": {"columns": ["price"], "method": "standard"}}
                            ]
                        },
                        "pipeline_name": "sales_preprocessing"
                    }
                },
                {
                    "type": "training",
                    "config": {
                        "model_type": "xgboost",
                        "target_column": "sales",
                        "feature_columns": ["price", "quantity"],
                        "register_model": True,
                        "model_name": "sales_model"
                    }
                }
            ],
            description="Sales prediction pipeline with preprocessing and XGBoost"
        )
    """
    try:
        # Validate steps
        if not steps_config:
            return ToolResponse(
                payload=None,
                summary="Error: Pipeline must have at least one step",
                metadata={"error": "ValidationError"},
                storage_hint="never",
            )

        # Create pipeline steps
        steps = []
        for i, step_config in enumerate(steps_config):
            step_type_str = step_config.get("type")
            step_params = step_config.get("config", {})

            # Validate step type
            try:
                step_type = PipelineStepType(step_type_str)
            except ValueError:
                valid_types = [t.value for t in PipelineStepType]
                return ToolResponse(
                    payload=None,
                    summary=f"Error in step {i + 1}: Invalid type '{step_type_str}'. Valid types: {valid_types}",
                    metadata={"error": "ValidationError", "valid_types": valid_types},
                    storage_hint="never",
                )

            step = PipelineStep(type=step_type, config=step_params)
            steps.append(step)

        # Create pipeline
        pipeline = Pipeline(
            name=name,
            description=description,
            steps=steps,
        )

        # Save pipeline to storage
        registry = get_repository_registry()

        # Create a repository for pipelines (using tool_response for now)
        pipeline_data = {
            "entity_id": pipeline.entity_id,
            "name": pipeline.name,
            "description": pipeline.description,
            "steps": [step.model_dump() for step in pipeline.steps],
            "status": pipeline.status.value,
            "created_at": pipeline.created_at.isoformat(),
        }

        pipeline_response = ToolResponse(
            payload=pipeline_data,
            summary=f"Pipeline '{name}' created",
            metadata={"pipeline_id": pipeline.entity_id, "num_steps": len(steps)},
            storage_hint="session",
            suggested_name=f"pipeline_{name}",
        )
        pipeline_response.entity_id = pipeline.entity_id

        tool_response_repo = registry.get_repository("tool_response")
        await tool_response_repo.save(pipeline_response)

        # Generate summary
        summary = "✅ Pipeline created successfully!\n\n"
        summary += f"Name: {name}\n"
        summary += f"Pipeline ID: {pipeline.entity_id}\n"
        summary += f"Steps: {len(steps)}\n"

        if description:
            summary += f"Description: {description}\n"

        summary += "\nPipeline Steps:\n"
        for i, step in enumerate(steps):
            summary += f"  {i + 1}. {step.type.value}\n"

        summary += "\nTo execute this pipeline, use:\n"
        summary += f"  run_pipeline(pipeline_id='{pipeline.entity_id}')"

        return ToolResponse(
            payload=pipeline_data,
            summary=summary,
            metadata={
                "pipeline_id": pipeline.entity_id,
                "name": name,
                "num_steps": len(steps),
            },
            storage_hint="session",
            suggested_name=f"pipeline_config_{name}",
        )

    except Exception as e:
        logger.exception(f"Error creating pipeline: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error creating pipeline: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

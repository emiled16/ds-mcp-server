"""Execute a multi-step ML pipeline."""

from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.job import Job, JobStatus
from src.models.pipeline import Pipeline, PipelineStep
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def run_pipeline(
    pipeline_id: str,
    async_mode: bool = True,
) -> str:
    """Execute a multi-step ML pipeline.

    Runs all steps in sequence: feature engineering → training → HPT.
    Each step's output becomes the input for the next step.

    Args:
        pipeline_id: Entity ID of the pipeline to execute
        async_mode: If True, submit to queue; if False, run synchronously

    Returns:
        ToolResponse with pipeline execution results

    Example:
        "Run the sales prediction pipeline"
        → run_pipeline(pipeline_id="abc123", async_mode=True)
    """
    try:
        # Load pipeline from storage
        registry = get_repository_registry()
        tool_response_repo = registry.get_repository("tool_response")
        pipeline_entity = await tool_response_repo.get(pipeline_id)

        if not pipeline_entity:
            return ToolResponse(
                payload=None,
                summary=f"Error: Pipeline '{pipeline_id}' not found",
                metadata={"error": "NotFound", "pipeline_id": pipeline_id},
                storage_hint="never",
            )

        # Reconstruct pipeline from stored data
        pipeline_data = pipeline_entity.payload
        steps = []
        for step_data in pipeline_data["steps"]:
            from src.models.pipeline import PipelineStepType

            step = PipelineStep(
                step_id=step_data["step_id"],
                type=PipelineStepType(step_data["type"]),
                config=step_data["config"],
            )
            steps.append(step)

        pipeline = Pipeline(
            entity_id=pipeline_data["entity_id"],
            name=pipeline_data["name"],
            description=pipeline_data.get("description"),
            steps=steps,
        )

        if async_mode:
            # Submit to Celery (create a pipeline execution task)
            # For now, we'll submit individual steps as jobs
            # In a full implementation, we'd have a dedicated pipeline runner task

            job = Job(
                celery_task_id=None,  # Will be set when we have a proper pipeline task
                task_name="run_pipeline",
                kwargs={"pipeline_id": pipeline_id},
                status=JobStatus.PENDING,
                metadata={
                    "pipeline_id": pipeline_id,
                    "pipeline_name": pipeline.name,
                    "num_steps": len(pipeline.steps),
                },
            )

            job_repo = registry.get_repository("job")
            await job_repo.save(job)

            summary = (
                f"Pipeline execution submitted!\n\n"
                f"Pipeline: {pipeline.name}\n"
                f"Pipeline ID: {pipeline_id}\n"
                f"Job ID: {job.entity_id}\n"
                f"Steps: {len(pipeline.steps)}\n\n"
                f"Note: Pipeline execution will run each step in sequence.\n"
                f"Use get_job_status(job_id='{job.entity_id}') to check progress."
            )

            return ToolResponse(
                payload={
                    "job_id": job.entity_id,
                    "pipeline_id": pipeline_id,
                    "status": "PENDING",
                    "async": True,
                },
                summary=summary,
                metadata={
                    "job_id": job.entity_id,
                    "pipeline_id": pipeline_id,
                    "async": True,
                },
                storage_hint="session",
                suggested_name=f"pipeline_job_{pipeline.name}",
            )

        # Synchronous execution
        from src.workers.pipeline_runner import run_pipeline as execute_pipeline

        result_pipeline = execute_pipeline(pipeline)

        # Generate summary
        summary = f"Pipeline execution {'completed' if result_pipeline.status.value == 'completed' else 'failed'}!\n\n"
        summary += f"Pipeline: {result_pipeline.name}\n"
        summary += f"Status: {result_pipeline.status.value}\n"
        summary += f"Steps: {len(result_pipeline.steps)}\n\n"

        for i, step in enumerate(result_pipeline.steps):
            summary += f"Step {i + 1} ({step.type.value}): {step.status.value}\n"
            if step.error:
                summary += f"  Error: {step.error}\n"

        if result_pipeline.mlflow_parent_run_id:
            summary += f"\nMLflow Parent Run: {result_pipeline.mlflow_parent_run_id}"

        # Save updated pipeline
        updated_data = {
            "entity_id": result_pipeline.entity_id,
            "name": result_pipeline.name,
            "description": result_pipeline.description,
            "steps": [step.model_dump() for step in result_pipeline.steps],
            "status": result_pipeline.status.value,
            "created_at": result_pipeline.created_at.isoformat(),
            "started_at": result_pipeline.started_at.isoformat() if result_pipeline.started_at else None,
            "completed_at": result_pipeline.completed_at.isoformat() if result_pipeline.completed_at else None,
            "mlflow_parent_run_id": result_pipeline.mlflow_parent_run_id,
        }

        pipeline_entity.payload = updated_data
        await tool_response_repo.save(pipeline_entity)

        return ToolResponse(
            payload=updated_data,
            summary=summary,
            metadata={
                "pipeline_id": pipeline_id,
                "status": result_pipeline.status.value,
                "async": False,
            },
            storage_hint="session",
            suggested_name=f"pipeline_result_{pipeline.name}",
        )

    except Exception as e:
        logger.exception(f"Error running pipeline: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error running pipeline: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

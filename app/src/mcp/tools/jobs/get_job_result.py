"""Get job result tool."""

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.job import JobStatus
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def get_job_result(job_id: str) -> str:
    """Retrieve the result of a completed async job.

    Gets the output data from a job that has completed successfully.
    The job must be in SUCCESS status.

    Args:
        job_id: Job entity ID (e.g., 'job_abc123')

    Returns:
        ToolResponse with job results

    Example:
        "Get results from job_abc123"
        → get_job_result(job_id="job_abc123")
    """
    try:
        registry = get_repository_registry()
        job_repo = registry.get_repository("job")
        job = await job_repo.get(job_id)

        if not job:
            return ToolResponse(
                payload=None,
                summary=f"Error: Job '{job_id}' not found.",
                metadata={"error": "NotFound", "job_id": job_id},
                storage_hint="never",
            )

        # Check if job is complete
        if not job.is_complete:
            return ToolResponse(
                payload=None,
                summary=f"Job '{job_id}' is not complete yet.\n"
                f"Current status: {job.status.value}\n"
                "Use get_job_status() to monitor progress.",
                metadata={"error": "NotComplete", "status": job.status.value},
                storage_hint="never",
            )

        # Check if job succeeded
        if job.status != JobStatus.SUCCESS:
            return ToolResponse(
                payload=None,
                summary=f"Job '{job_id}' did not complete successfully.\n"
                f"Status: {job.status.value}\n"
                f"Error: {job.error or 'Unknown error'}",
                metadata={
                    "error": "JobFailed",
                    "status": job.status.value,
                    "job_error": job.error,
                },
                storage_hint="never",
            )

        # Return the result
        result = job.result

        # Generate summary based on result type
        if isinstance(result, dict):
            summary = f"Job '{job_id}' completed successfully:\n\n"
            for key, value in list(result.items())[:10]:
                if isinstance(value, (list, dict)):
                    summary += f"  • {key}: {type(value).__name__} with {len(value)} items\n"
                else:
                    summary += f"  • {key}: {value}\n"
            if len(result) > 10:
                summary += f"  ... and {len(result) - 10} more fields\n"
        else:
            summary = f"Job '{job_id}' completed successfully.\n"
            summary += f"Result type: {type(result).__name__}\n"

        summary += f"\nDuration: {job.duration_seconds:.1f} seconds" if job.duration_seconds else ""

        return ToolResponse(
            payload=result,
            summary=summary,
            metadata={
                "job_id": job_id,
                "task_name": job.task_name,
                "duration_seconds": job.duration_seconds,
            },
            storage_hint="session",
            suggested_name=f"job_{job.task_name}_result",
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error getting job result: {e}",
            metadata={"error": type(e).__name__, "job_id": job_id},
            storage_hint="never",
        )

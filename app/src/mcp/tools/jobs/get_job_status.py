"""Get job status tool."""

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.job import JobStatus
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def get_job_status(job_id: str) -> str:
    """Get the current status of an async job.

    Retrieves the status and metadata for a job submitted to the task queue.

    Args:
        job_id: Job entity ID (e.g., 'job_abc123')

    Returns:
        ToolResponse with job status information

    Example:
        "Check status of job_abc123"
        → get_job_status(job_id="job_abc123")
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

        # Generate status summary
        status_emoji = {
            JobStatus.PENDING: "⏳",
            JobStatus.STARTED: "🚀",
            JobStatus.RUNNING: "⚙️",
            JobStatus.RETRY: "🔄",
            JobStatus.SUCCESS: "✅",
            JobStatus.FAILURE: "❌",
            JobStatus.REVOKED: "🚫",
        }

        emoji = status_emoji.get(job.status, "❓")
        summary = f"Job Status: {emoji} {job.status.value}\n\n"
        summary += f"Job ID: {job.entity_id}\n"
        summary += f"Task: {job.task_name}\n"
        summary += f"Created: {job.created_at.isoformat()}\n"

        if job.started_at:
            summary += f"Started: {job.started_at.isoformat()}\n"

        if job.completed_at:
            summary += f"Completed: {job.completed_at.isoformat()}\n"
            if job.duration_seconds:
                summary += f"Duration: {job.duration_seconds:.1f} seconds\n"

        if job.error:
            summary += f"\nError: {job.error}\n"

        if job.is_complete:
            if job.status == JobStatus.SUCCESS:
                summary += "\nJob completed successfully. Use get_job_result() to retrieve results."
            elif job.status == JobStatus.FAILURE:
                summary += "\nJob failed. Check the error message above."
        else:
            summary += "\nJob is still running. Check again later."

        return ToolResponse(
            payload={
                "job_id": job.entity_id,
                "status": job.status.value,
                "task_name": job.task_name,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "duration_seconds": job.duration_seconds,
                "is_complete": job.is_complete,
                "error": job.error,
            },
            summary=summary,
            metadata={"job_id": job_id},
            storage_hint="never",
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error getting job status: {e}",
            metadata={"error": type(e).__name__, "job_id": job_id},
            storage_hint="never",
        )

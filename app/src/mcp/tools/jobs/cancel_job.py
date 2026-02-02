"""Cancel job tool."""

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.job import JobStatus
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry
from src.workers.celery_app import app as celery_app


@mcp.tool
@process_tool
@register_tool
async def cancel_job(job_id: str, force: bool = False) -> str:
    """Cancel a running or pending async job.

    Attempts to revoke a job from the task queue. Jobs that are already
    running may not be immediately cancellable unless force=True.

    Args:
        job_id: Job entity ID (e.g., 'job_abc123')
        force: If True, terminate the task immediately (may cause data loss)

    Returns:
        ToolResponse with cancellation status

    Example:
        "Cancel job_abc123"
        → cancel_job(job_id="job_abc123")

        "Force cancel job_abc123"
        → cancel_job(job_id="job_abc123", force=True)
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

        # Check if job is already complete
        if job.is_complete:
            return ToolResponse(
                payload={"cancelled": False, "reason": "already_complete"},
                summary=f"Job '{job_id}' is already complete ({job.status.value}).\nCannot cancel a completed job.",
                metadata={"job_id": job_id, "status": job.status.value},
                storage_hint="never",
            )

        # Revoke the Celery task
        try:
            celery_app.control.revoke(
                job.celery_task_id,
                terminate=force,
                signal="SIGKILL" if force else "SIGTERM",
            )
        except Exception as e:
            return ToolResponse(
                payload={"cancelled": False, "reason": str(e)},
                summary=f"Failed to cancel job in task queue: {e}\nThe job may still be running.",
                metadata={"error": "RevokeFailed", "details": str(e)},
                storage_hint="never",
            )

        # Update job status
        job = await job_repo.update_status(
            job_id,
            JobStatus.REVOKED,
            error="Cancelled by user" + (" (forced)" if force else ""),
        )

        summary = f"Job '{job_id}' has been cancelled.\n\n"
        summary += f"Task: {job.task_name}\n"
        summary += f"Previous status: {job.status.value}\n"
        summary += f"Force terminated: {'Yes' if force else 'No'}\n"

        if force:
            summary += "\n⚠️ Job was force-terminated. Any partial results may be lost."

        return ToolResponse(
            payload={
                "cancelled": True,
                "job_id": job_id,
                "force": force,
            },
            summary=summary,
            metadata={"job_id": job_id, "force": force},
            storage_hint="never",
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error cancelling job: {e}",
            metadata={"error": type(e).__name__, "job_id": job_id},
            storage_hint="never",
        )

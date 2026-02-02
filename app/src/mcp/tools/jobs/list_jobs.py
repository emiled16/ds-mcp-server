"""List jobs tool."""

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.job import JobStatus
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def list_jobs(
    status: str | None = None,
    limit: int = 20,
) -> str:
    """List async jobs with optional filtering.

    Shows all jobs or filters by status.

    Args:
        status: Optional status filter ('PENDING', 'RUNNING', 'SUCCESS', 'FAILURE', 'REVOKED')
        limit: Maximum number of jobs to return (default: 20)

    Returns:
        ToolResponse with list of jobs

    Example:
        "Show all jobs"
        → list_jobs()

        "Show only running jobs"
        → list_jobs(status="RUNNING")

        "Show last 50 jobs"
        → list_jobs(limit=50)
    """
    try:
        registry = get_repository_registry()
        job_repo = registry.get_repository("job")

        # Build filter
        filters = {}
        if status:
            # Validate status
            try:
                job_status = JobStatus(status.upper())
                filters["status"] = job_status.value
            except ValueError:
                valid = [s.value for s in JobStatus]
                return ToolResponse(
                    payload=None,
                    summary=f"Invalid status '{status}'. Valid options: {valid}",
                    metadata={"error": "InvalidStatus", "valid_options": valid},
                    storage_hint="never",
                )

        # Get jobs
        jobs = await job_repo.list(filters)

        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        # Limit results
        jobs = jobs[:limit]

        if not jobs:
            summary = "No jobs found"
            if status:
                summary += f" with status '{status}'"
            summary += "."
            return ToolResponse(
                payload=[],
                summary=summary,
                metadata={"count": 0, "filter": filters},
                storage_hint="never",
            )

        # Status emoji mapping
        status_emoji = {
            JobStatus.PENDING: "⏳",
            JobStatus.STARTED: "🚀",
            JobStatus.RUNNING: "⚙️",
            JobStatus.RETRY: "🔄",
            JobStatus.SUCCESS: "✅",
            JobStatus.FAILURE: "❌",
            JobStatus.REVOKED: "🚫",
        }

        # Generate summary
        summary = f"Jobs ({len(jobs)}"
        if status:
            summary += f", filtered by {status}"
        summary += "):\n\n"

        summary += f"{'ID':<20} {'Status':<12} {'Task':<25} {'Created':<20}\n"
        summary += "-" * 80 + "\n"

        for job in jobs:
            emoji = status_emoji.get(job.status, "❓")
            created = job.created_at.strftime("%Y-%m-%d %H:%M")
            task_name = job.task_name[:22] + "..." if len(job.task_name) > 25 else job.task_name
            summary += f"{job.entity_id:<20} {emoji} {job.status.value:<10} {task_name:<25} {created}\n"

        # Add statistics
        pending = sum(1 for j in jobs if j.status == JobStatus.PENDING)
        running = sum(1 for j in jobs if j.status in [JobStatus.STARTED, JobStatus.RUNNING])
        success = sum(1 for j in jobs if j.status == JobStatus.SUCCESS)
        failed = sum(1 for j in jobs if j.status == JobStatus.FAILURE)

        summary += "\nSummary:\n"
        summary += f"  ⏳ Pending: {pending}  ⚙️ Running: {running}  ✅ Success: {success}  ❌ Failed: {failed}"

        # Convert to serializable format
        jobs_data = [
            {
                "job_id": j.entity_id,
                "status": j.status.value,
                "task_name": j.task_name,
                "created_at": j.created_at.isoformat(),
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "is_complete": j.is_complete,
            }
            for j in jobs
        ]

        return ToolResponse(
            payload=jobs_data,
            summary=summary,
            metadata={
                "count": len(jobs),
                "filter": filters,
                "pending": pending,
                "running": running,
                "success": success,
                "failed": failed,
            },
            storage_hint="never",
        )

    except Exception as e:
        return ToolResponse(
            payload=None,
            summary=f"Error listing jobs: {e}",
            metadata={"error": type(e).__name__},
            storage_hint="never",
        )

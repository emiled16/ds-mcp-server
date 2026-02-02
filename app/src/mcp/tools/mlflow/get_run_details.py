"""Get detailed information about a specific MLflow run."""

import os

import mlflow
from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_SERVER_URL", os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))


@mcp.tool
@process_tool
@register_tool
async def get_run_details(
    run_id: str,
) -> str:
    """Get detailed information about a specific MLflow run.

    Returns comprehensive information about a run including all metrics,
    parameters, tags, and artifacts.

    Args:
        run_id: MLflow run ID

    Returns:
        ToolResponse with detailed run information

    Example:
        "Show me details for this run"
        → get_run_details(run_id="abc123def456")
    """
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = mlflow.tracking.MlflowClient()

        # Get run
        try:
            run = client.get_run(run_id)
        except Exception as e:
            logger.exception(f"Error fetching run: {e}")
            return ToolResponse(
                payload=None,
                summary=f"Error: Run '{run_id}' not found: {e}",
                metadata={"error": "NotFound", "run_id": run_id, "details": str(e)},
                storage_hint="never",
            )

        # Get experiment info
        experiment = client.get_experiment(run.info.experiment_id)

        # Get artifacts
        artifacts = []
        try:
            artifacts = client.list_artifacts(run_id)
        except Exception as e:
            logger.warning(f"Could not list artifacts: {e}")

        # Build detailed data
        run_details = {
            "run_id": run.info.run_id,
            "run_name": run.info.run_name,
            "experiment_id": run.info.experiment_id,
            "experiment_name": experiment.name if experiment else None,
            "status": run.info.status,
            "start_time": run.info.start_time,
            "end_time": run.info.end_time,
            "lifecycle_stage": run.info.lifecycle_stage,
            "artifact_uri": run.info.artifact_uri,
            "metrics": run.data.metrics,
            "params": run.data.params,
            "tags": run.data.tags,
            "artifacts": [{"path": a.path, "is_dir": a.is_dir, "file_size": a.file_size} for a in artifacts],
        }

        # Calculate duration
        duration_ms = None
        if run.info.end_time and run.info.start_time:
            duration_ms = run.info.end_time - run.info.start_time

        # Generate summary
        summary = "📋 Run Details\n\n"
        summary += f"Run ID: {run.info.run_id}\n"
        summary += f"Name: {run.info.run_name or 'N/A'}\n"
        summary += f"Status: {run.info.status}\n"
        summary += f"Experiment: {experiment.name if experiment else run.info.experiment_id}\n"

        if duration_ms:
            duration_sec = duration_ms / 1000
            if duration_sec < 60:
                summary += f"Duration: {duration_sec:.1f} seconds\n"
            elif duration_sec < 3600:
                summary += f"Duration: {duration_sec / 60:.1f} minutes\n"
            else:
                summary += f"Duration: {duration_sec / 3600:.1f} hours\n"

        # Metrics
        if run.data.metrics:
            summary += f"\nMetrics ({len(run.data.metrics)}):\n"
            for metric, value in sorted(run.data.metrics.items()):
                summary += f"  • {metric}: {value:.4f}\n"

        # Parameters
        if run.data.params:
            summary += f"\nParameters ({len(run.data.params)}):\n"
            for param, value in sorted(run.data.params.items()):
                summary += f"  • {param}: {value}\n"

        # Tags
        if run.data.tags:
            summary += f"\nTags ({len(run.data.tags)}):\n"
            for tag, value in sorted(run.data.tags.items())[:10]:
                summary += f"  • {tag}: {value}\n"
            if len(run.data.tags) > 10:
                summary += f"  ... and {len(run.data.tags) - 10} more tags\n"

        # Artifacts
        if artifacts:
            summary += f"\nArtifacts ({len(artifacts)}):\n"
            for artifact in artifacts[:10]:
                if artifact.is_dir:
                    summary += f"  📁 {artifact.path}/\n"
                else:
                    size_kb = artifact.file_size / 1024 if artifact.file_size else 0
                    summary += f"  📄 {artifact.path} ({size_kb:.1f} KB)\n"
            if len(artifacts) > 10:
                summary += f"  ... and {len(artifacts) - 10} more artifacts\n"

        summary += f"\nArtifact URI: {run.info.artifact_uri}"

        return ToolResponse(
            payload=run_details,
            summary=summary,
            metadata={
                "run_id": run_id,
                "experiment_id": run.info.experiment_id,
                "status": run.info.status,
                "num_metrics": len(run.data.metrics),
                "num_params": len(run.data.params),
                "num_artifacts": len(artifacts),
            },
            storage_hint="session",
            suggested_name=f"run_details_{run_id[:8]}",
        )

    except Exception as e:
        logger.exception(f"Error getting run details: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error getting run details: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

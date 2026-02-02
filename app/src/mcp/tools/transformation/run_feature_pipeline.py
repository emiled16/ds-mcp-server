"""Run a saved feature pipeline on new data."""

import mlflow
import pandas as pd
from loguru import logger

from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.mcp.tools import register_tool
from src.models.tool_response import ToolResponse
from src.storage.repositories.registry import get_repository_registry


@mcp.tool
@process_tool
@register_tool
async def run_feature_pipeline(
    dataset_id: str,
    pipeline_run_id: str,
) -> str:
    """Run a saved feature pipeline on new data.

    Loads a previously created feature pipeline from MLflow and applies
    it to a new dataset. The pipeline must have been created with
    create_feature_pipeline().

    Args:
        dataset_id: Entity ID of the dataset to transform
        pipeline_run_id: MLflow run ID of the saved pipeline

    Returns:
        ToolResponse with transformed data

    Example:
        "Apply the preprocessing pipeline to the test data"
        → run_feature_pipeline(
            dataset_id="test_data_123",
            pipeline_run_id="abc123def456"
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

        # Load pipeline from MLflow
        logger.info(f"Loading pipeline from MLflow run: {pipeline_run_id}")
        model_uri = f"runs:/{pipeline_run_id}/pipeline"

        try:
            pipeline = mlflow.pyfunc.load_model(model_uri)
        except Exception as e:
            logger.exception(f"Error loading pipeline from MLflow: {e}")
            return ToolResponse(
                payload=None,
                summary=f"Error loading pipeline from MLflow run '{pipeline_run_id}': {e}",
                metadata={"error": "MLflowLoadError", "details": str(e)},
                storage_hint="never",
            )

        # Apply pipeline
        original_shape = df.shape
        logger.info(f"Applying pipeline to data: {original_shape[0]:,} rows × {original_shape[1]} columns")

        try:
            transformed_df = pipeline.predict(df)
        except Exception as e:
            logger.exception(f"Error applying pipeline: {e}")
            return ToolResponse(
                payload=None,
                summary=f"Error applying pipeline: {e}",
                metadata={"error": "PipelineTransformError", "details": str(e)},
                storage_hint="never",
            )

        # Generate summary
        new_shape = transformed_df.shape
        new_cols = set(transformed_df.columns) - set(df.columns)
        removed_cols = set(df.columns) - set(transformed_df.columns)

        summary = "✅ Pipeline applied successfully!\n\n"
        summary += f"Pipeline Run ID: {pipeline_run_id}\n"
        summary += f"Original: {original_shape[0]:,} rows × {original_shape[1]} columns\n"
        summary += f"Transformed: {new_shape[0]:,} rows × {new_shape[1]} columns\n"

        if new_cols:
            summary += f"\nNew columns ({len(new_cols)}): {', '.join(list(new_cols)[:10])}"
            if len(new_cols) > 10:
                summary += f"... +{len(new_cols) - 10} more"
            summary += "\n"

        if removed_cols:
            summary += f"\nRemoved columns ({len(removed_cols)}): {', '.join(list(removed_cols)[:10])}"
            if len(removed_cols) > 10:
                summary += f"... +{len(removed_cols) - 10} more"
            summary += "\n"

        # Preview
        preview = transformed_df.head(3).to_string(max_cols=10, max_colwidth=30)
        summary += f"\nPreview:\n{preview}"

        return ToolResponse(
            payload=transformed_df,
            summary=summary,
            metadata={
                "dataset_id": dataset_id,
                "pipeline_run_id": pipeline_run_id,
                "original_shape": original_shape,
                "transformed_shape": new_shape,
                "new_columns": list(new_cols),
                "removed_columns": list(removed_cols),
            },
            storage_hint="session",
            suggested_name=f"{entity.suggested_name or 'data'}_pipeline_transformed",
        )

    except Exception as e:
        logger.exception(f"Error running feature pipeline: {e}")
        return ToolResponse(
            payload=None,
            summary=f"Error running feature pipeline: {e}",
            metadata={"error": type(e).__name__, "details": str(e)},
            storage_hint="never",
        )

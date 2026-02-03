"""MCP HTTP Server - FastMCP streamable-http transport for Cursor MCP.

This server uses FastMCP's run() method with streamable-http transport,
which is compatible with Cursor's MCP HTTP transport.

Usage in Docker:
    python -m src.mcp.server

Configuration in Cursor mcp.json:
{
  "mcpServers": {
    "maxa-data-scientist": {
      "type": "http",
      "url": "http://localhost:8001/mcp"
    }
  }
}
"""

import asyncio
import logging
import os

# Data tools (list datasets)
import src.mcp.tools.data

# Data access tools
import src.mcp.tools.data_access.get_dataset_lineage
import src.mcp.tools.data_access.list_transformed_datasets
import src.mcp.tools.data_access.load_csv
import src.mcp.tools.data_access.load_dataset
import src.mcp.tools.data_access.load_excel
import src.mcp.tools.data_access.load_transformed_dataset

# Model Evaluation tools
import src.mcp.tools.evaluation.compare_models
import src.mcp.tools.evaluation.cross_validate
import src.mcp.tools.evaluation.evaluate_model

# Model Explainability tools
import src.mcp.tools.explainability.explain_prediction
import src.mcp.tools.explainability.explain_with_lime
import src.mcp.tools.explainability.explain_with_shap
import src.mcp.tools.explainability.plot_feature_contributions
import src.mcp.tools.explainability.plot_partial_dependence

# Data exploration tools
import src.mcp.tools.exploration.analyze_correlations
import src.mcp.tools.exploration.describe_dataset
import src.mcp.tools.exploration.detect_missing_values
import src.mcp.tools.exploration.profile_data

# Inference tools
import src.mcp.tools.inference.batch_predict
import src.mcp.tools.inference.load_model
import src.mcp.tools.inference.predict
import src.mcp.tools.inference.predict_with_pipeline

# Job management tools
import src.mcp.tools.jobs.cancel_job
import src.mcp.tools.jobs.get_job_result
import src.mcp.tools.jobs.get_job_status
import src.mcp.tools.jobs.list_jobs
import src.mcp.tools.jobs.submit_training_job

# Meta tools (tool descriptions, session management)
import src.mcp.tools.meta
import src.mcp.tools.meta.list_stored_entities

# MLflow Management tools
import src.mcp.tools.mlflow.compare_runs
import src.mcp.tools.mlflow.get_run_details
import src.mcp.tools.mlflow.list_experiments
import src.mcp.tools.mlflow.list_runs
import src.mcp.tools.mlflow.search_runs

# MLflow Model Registry tools
import src.mcp.tools.models.get_model_version
import src.mcp.tools.models.list_registered_models
import src.mcp.tools.models.promote_model_stage

# Note-taking tools
import src.mcp.tools.notes.append_to_note
import src.mcp.tools.notes.create_note
import src.mcp.tools.notes.get_note
import src.mcp.tools.notes.list_notes
import src.mcp.tools.notes.search_notes
import src.mcp.tools.notes.update_note

# Pipeline orchestration tools
import src.mcp.tools.pipeline.create_pipeline
import src.mcp.tools.pipeline.run_pipeline

# Statistical Analysis tools
import src.mcp.tools.statistics.ab_test
import src.mcp.tools.statistics.confidence_interval
import src.mcp.tools.statistics.hypothesis_test
import src.mcp.tools.statistics.significance_test

# Transformation/Feature engineering tools
import src.mcp.tools.transformation.apply_transformation
import src.mcp.tools.transformation.create_feature_pipeline
import src.mcp.tools.transformation.list_transformations
import src.mcp.tools.transformation.run_feature_pipeline

# Data Validation tools
import src.mcp.tools.validation.check_quality
import src.mcp.tools.validation.detect_drift
import src.mcp.tools.validation.detect_outliers
import src.mcp.tools.validation.validate_schema
import src.mcp.tools.validation.validate_types

# Visualization tools
import src.mcp.tools.visualization.plot_confusion_matrix
import src.mcp.tools.visualization.plot_correlation_heatmap
import src.mcp.tools.visualization.plot_distribution
import src.mcp.tools.visualization.plot_feature_importance
import src.mcp.tools.visualization.plot_learning_curves
import src.mcp.tools.visualization.plot_precision_recall_curve
import src.mcp.tools.visualization.plot_residuals
import src.mcp.tools.visualization.plot_roc_curve  # noqa: F401
from src.mcp.instance import mcp
from src.storage.backends.dispatcher import get_object_store
from src.storage.backends.postgres_document_store import PostgresDocumentStore
from src.storage.repositories.registry import RepositoryRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _postgres_doc_store() -> PostgresDocumentStore:
    """Build PostgresDocumentStore from env (POSTGRES_*)."""
    return PostgresDocumentStore(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "maxa_ds"),
        user=os.getenv("POSTGRES_USER", "appuser"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        schema=os.getenv("POSTGRES_SCHEMA", "app"),
    )


async def initialize_storage() -> None:
    """Initialize Postgres and object store (MinIO or GCS) backends."""
    logger.info("Initializing storage backends...")
    doc_store = _postgres_doc_store()
    obj_store = get_object_store()
    registry = RepositoryRegistry(document_store=doc_store, object_store=obj_store)
    await registry.initialize()
    logger.info("Storage backends initialized successfully")


def main() -> None:
    """Run the MCP HTTP server using FastMCP's streamable-http transport."""
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8001"))

    logger.info(f"Starting MCP HTTP Server on {host}:{port}")
    logger.info("Using FastMCP streamable-http transport")
    logger.info(f"MCP endpoint will be available at: http://{host}:{port}")

    # Initialize storage backends in async context
    asyncio.run(initialize_storage())

    # Start the FastMCP server with streamable-http transport
    # mcp.run() manages its own event loop, so we call it synchronously
    logger.info("Starting MCP server...")
    mcp.run(transport="streamable-http", host=host, port=port)


if __name__ == "__main__":
    main()

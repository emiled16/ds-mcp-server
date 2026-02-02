# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MAXA Data Scientist is an AI-powered data science assistant that provides a natural language interface for data science workflows. The system integrates Claude AI with data processing, feature engineering, model training, and MLOps capabilities through a Model Context Protocol (MCP) server architecture.

**Important Documentation**:
- `docs/CONTEXT.md` - Project vision and problem statement
- `docs/ARCHITECTURE.md` - Current state, vision requirements, and potential improvements
- `docs/IMPLEMENTATION_PLAN.md` - Detailed 6-week plan to implement core vision

## Development Commands

### Environment Setup
```bash
# Install dependencies using Poetry
poetry install

# Activate virtual environment
poetry shell

# Copy environment template and configure
cp .env.example .env
# Edit .env with your GCP project, Snowflake credentials (if needed), etc.
```

### Running the Application

**Start all services (Docker Compose - Recommended):**
```bash
cd docker
docker compose up -d
```

This starts:
- MCP server (port 8001)
- MLflow tracking server (port 5000)
- MongoDB (port 27017)
- MinIO (ports 9000/9001)
- PostgreSQL (for MLflow backend)

**Run MCP server standalone:**
```bash
python -m src.mcp.server
```

### Testing
```bash
# Run tests with pytest
pytest

# Run specific test file
pytest tests/test_file.py

# Run with coverage
pytest --cov=src
```

### Code Quality
```bash
# Run ruff linter
ruff check .

# Run ruff formatter
ruff format .

# Fix auto-fixable issues
ruff check --fix .
```

## Architecture

### High-Level Structure

The codebase is organized into two main domains:

1. **MCP Server Layer** (`src/mcp/`): FastMCP-based HTTP server that exposes data science tools to Claude AI
2. **Data Science Layer** (`src/data_science/`): Core data science pipelines, feature engineering, and ML workflows

### MCP Server Architecture

The MCP (Model Context Protocol) server uses **FastMCP** with `streamable-http` transport to communicate with Claude AI clients (Cursor, etc.).

**Key components:**
- `src/mcp/instance.py`: Singleton MCP instance (`mcp = FastMCP("DataScienceToolbox")`)
- `src/mcp/server.py`: HTTP server entry point that starts FastMCP with streamable-http transport
- `src/mcp/tools/`: Tool implementations decorated with `@mcp.tool` and `@process_tool`
- `src/mcp/middleware.py`: `@process_tool` decorator that handles async execution and tool response formatting

**Tool Response Pattern:**
All tools return `ToolResponse` objects with:
- `payload`: Actual data (can be stored in MinIO if large)
- `summary`: Human-readable summary for Claude
- `metadata`: Additional context
- `storage_hint`: Controls caching behavior ("never", "session", "permanent")

Tools are automatically registered with FastMCP via decorators. To add a new tool:
1. Create tool function in `src/mcp/tools/`
2. Decorate with `@mcp.tool` and `@process_tool`
3. Import in `src/mcp/server.py` (commented imports show existing tool structure)

### Storage Architecture

The project implements a **Repository pattern** with two storage backends:

1. **DocumentStore** (MongoDB): Stores metadata and small documents
2. **ObjectStore** (MinIO/S3): Stores large binary objects (DataFrames, models, artifacts)

**Key interfaces:**
- `src/storage/interfaces.py`: Defines `DocumentStore`, `ObjectStore`, `BaseRepository` interfaces
- `src/storage/backends/`: Concrete implementations (MongoDB, MinIO)
- `src/storage/repositories/`: Domain-specific repositories (e.g., `ToolResponseRepository`)
- `src/storage/repositories/registry.py`: `RepositoryRegistry` for dependency injection

**Storage pattern:**
- DataFrames exceeding `MINIO_SIZE_THRESHOLD_MB` (default 0.5MB) are automatically offloaded to MinIO
- Repositories handle serialization (pickle, JSON) transparently
- Use `get_repository_registry()` to access repositories in tools

### Data Science Layer

The data science layer follows a **pipeline-based architecture** where experiments consist of:
1. Use case definition
2. Experiment configuration
3. Feature store pipeline
4. Model selection/training
5. Hyperparameter tuning
6. Inference

**Key modules:**

- **`src/data_science/pipelines/`**: High-level orchestration for experiments, feature stores, model training, inference
  - `experiment.py`: Creates experiment records
  - `feature_store.py`: Builds and persists feature pipelines
  - `model_selection.py`: Model training and evaluation
  - `hyperparameter_tuning.py`: Optuna-based hyperparameter optimization
  - `inference.py`: Batch and real-time inference

- **`src/data_science/feature_store/`**: Transformation library for feature engineering
  - Uses a custom pipeline framework with `fit`/`transform` pattern
  - Supports both Pandas and Snowpark DataFrames
  - Transformations include: aggregation, lag features, cyclic time encoding, one-hot encoding, etc.
  - Custom transformations inherit from `BaseTransformation` with `_transform_pandas` and `_transform_snowpark` methods

- **`src/data_science/database/`**: Database client abstraction
  - `DBClient`: Unified interface for Snowflake operations
  - Handles table CRUD, file uploads/downloads, query execution
  - Models in `database/models/` define Snowflake table schemas

- **`src/data_science/definitions/`**: Configuration schemas
  - Pydantic models for experiment configs, feature pipelines, model configs
  - `configs/experiment.py`: `ExperimentPipelineConfig`
  - `configs/feature_store.py`: `FeaturePipelineConfig`

- **`src/data_science/features/`**: Specific feature implementations
  - Time series features: rolling windows, calendar features, lag features
  - Target-oriented features for treasury forecasting use case

- **`src/data_science/snowflake/`**: Snowflake-specific utilities
  - Session management, transaction handling
  - Cortex AI integration for semantic queries
  - Table utilities and identifier handling

### Configuration Management

The project uses multiple configuration layers:

1. **Environment variables** (`.env`): Infrastructure and service URLs
2. **Pydantic settings**: Type-safe configuration loading
3. **Experiment configs**: Stored in database as JSON, validated with Pydantic

**Critical environment variables:**
- `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`: For Vertex AI
- `SNOWFLAKE_*`: Snowflake credentials and connection details
- `MCP_URL`, `MCP_TRANSPORT`: MCP server configuration
- `REDIS_URL`, `MONGODB_*`, `MINIO_*`: Storage backends
- `MLFLOW_TRACKING_URI`: MLflow server URL

### MLflow Integration

All experiments are tracked in MLflow:
- Metrics, parameters, and artifacts logged during training
- Models registered in MLflow Model Registry
- Feature pipelines stored as artifacts
- Use `MLFLOW_TRACKING_URI` to configure server endpoint

### Feature Store Pattern

Feature engineering uses a **fit-transform pipeline** pattern:
1. Define transformations in config (e.g., `FeaturePipelineConfig`)
2. Pipeline calls `generate_pipeline()` to build sklearn-like pipeline
3. `fit_transform()` on training data to learn parameters (e.g., encodings, statistics)
4. `transform()` on new data to apply learned transformations
5. Pipeline serialized and stored in Snowflake stage + database metadata

**Creating custom transformations:**
See `src/data_science/feature_store/library/README.md` for detailed instructions. Key points:
- Inherit from `BaseTransformation`
- Implement `_fit_pandas`, `_transform_pandas`, `_fit_snowpark`, `_transform_snowpark`
- Define `Parameters`, `Input`, `Output` classes with Pydantic

## Common Workflows

### Adding a New MCP Tool

1. Create tool file in `src/mcp/tools/your_tool.py`:
```python
from src.mcp.instance import mcp
from src.mcp.middleware import process_tool
from src.models.tool_response import ToolResponse

@mcp.tool
@process_tool
async def your_tool(param: str) -> str:
    """Tool description shown to Claude."""
    # Implementation
    return ToolResponse(
        payload=result_data,
        summary="Human-readable summary",
        metadata={},
        storage_hint="session"
    )
```

2. Import in `src/mcp/server.py`:
```python
import src.mcp.tools.your_tool  # noqa: F401
```

3. Restart MCP server

### Creating an Experiment Pipeline

1. Define use case in database (via `src/data_science/pipelines/use_case.py`)
2. Create experiment config (`ExperimentPipelineConfig`)
3. Run experiment pipeline: `create_experiment(config, db_client)`
4. Build feature store: `feature_store(feature_config, db_client, experiment_id)`
5. Train model: `model_selection(model_config, db_client, experiment_id)`
6. Tune hyperparameters: `hyperparameter_tuning(tuning_config, db_client, experiment_id)`

### Working with Snowflake

The `DBClient` provides high-level operations:
- `fetch_table(table_path)`: Returns Pandas DataFrame
- `fetch_records(model_class, filters)`: Query with filters
- `insert_records(model_class, records)`: Insert data
- `upload_files(path, identifier)`: Upload to Snowflake stage
- `download_files(stage_path, local_path)`: Download from stage

Snowflake session is managed automatically. For direct Snowpark operations, use `src.data_science.snowflake.session.get_active_session()`.

## Important Patterns

### Async Tool Execution

Tools can be executed synchronously or asynchronously (via Celery):
- Synchronous: Direct execution in MCP server
- Asynchronous: Submit to Celery worker, return job ID, poll for results
- Configure with `async_mode` parameter in tool calls

### Data Serialization

Large DataFrames are automatically offloaded to MinIO:
- Threshold configured by `MINIO_SIZE_THRESHOLD_MB`
- Serialization handled by repositories
- Tool responses reference object store keys instead of embedding data

### Error Handling

- Validation errors from Pydantic models provide clear feedback
- Database operations wrapped with logging (loguru)
- Use `get_tool_examples()` to see correct parameter formats
- Check `list_available_transformations()` before building pipelines

## Ruff Configuration

The project uses Ruff with strict linting (`select = ["ALL"]`) but ignores:
- Docstring lints (D)
- TODO formatting (TD, FIX)
- Type checking blocks (TCH)
- Error message rules (EM, TRY)
- Specific rules: `ANN101` (self hints), `S101` (assert), `S608` (raw SQL), `PD901` (df variable)

Use Google-style docstrings (`convention = "google"`).

## Key File Locations

- CLI entry point: `maxa-ds` command (defined in `pyproject.toml` scripts)
- MCP server entry: `python -m src.mcp.server`
- Dataset storage: `./datasets/` (mounted in Docker)
- Docker configs: `./docker/docker-compose.yaml`
- Environment template: `.env.example`

# Architecture Documentation

## Table of Contents
1. [Current State: What Exists](#current-state-what-exists)
2. [The Vision: What's Required](#the-vision-whats-required)
3. [Potential Improvements](#potential-improvements)

---

## Current State: What Exists

This section describes what has been implemented in the codebase as of now.

### Infrastructure Layer (Implemented ✅)

**Location**: `docker/docker-compose.yaml`

All infrastructure services are configured and ready:

1. **MongoDB** (port 27017) - Document store for metadata
2. **MinIO** (ports 9000/9001) - Object store for large artifacts
3. **PostgreSQL** (port 5432) - MLflow backend store
4. **MLflow Server** (port 5000) - Experiment tracking
5. **MCP Server** (port 8001) - FastMCP HTTP server

```bash
# Start all services
cd docker && docker compose up -d
```

### Storage Layer (Implemented ✅)

**Location**: `src/storage/`

A complete repository pattern implementation with dual storage backends:

**Interfaces** (`src/storage/interfaces.py`):
```python
class DocumentStore(ABC)  # MongoDB operations
class ObjectStore(ABC)     # MinIO operations
class BaseRepository(ABC)  # Domain repositories
```

**Implementations**:
- `MongoDBDocumentStore` (`src/storage/backends/document_store.py`)
- `MinIOObjectStore` (`src/storage/backends/object_store.py`)
- `ToolResponseRepository` (`src/storage/repositories/tool_response.py`)

**Registry** (`src/storage/repositories/registry.py`):
- Singleton pattern for centralized repository access
- Currently registers only `ToolResponseRepository`
- Provides `save()`, `get()`, `delete()`, `list()` operations

**Storage Logic**:
- Payloads > 0.5MB automatically stored in MinIO
- Metadata always stored in MongoDB
- Handles serialization (pickle for DataFrames, JSON for metadata)

### MCP Server (Partially Implemented ⚠️)

**Location**: `src/mcp/`

**What Works**:
- FastMCP instance (`src/mcp/instance.py`):
  ```python
  mcp = FastMCP("DataScienceToolbox")
  ```
- HTTP server with streamable-http transport (`src/mcp/server.py`)
- Storage initialization on startup
- Runs on `http://localhost:8001`

**Cursor Configuration**:
```json
{
  "mcpServers": {
    "maxa-data-scientist": {
      "type": "http",
      "url": "http://localhost:8001"
    }
  }
}
```

### Middleware (Basic Implementation ⚠️)

**Location**: `src/mcp/middleware.py`

**Current Features**:
- `@process_tool` decorator wraps all tools
- Calls tool function (sync or async)
- Returns `ToolResponse.summary` to agent
- Basic error handling

**Missing from Middleware** (mentioned in docstring but not implemented):
- ❌ Session context injection
- ❌ Caching and deduplication
- ❌ Async job support (Celery)
- ❌ MLflow integration
- ❌ Notebook updates
- ❌ Input parameter processing (entity_id resolution)

### Active MCP Tools (Minimal ⚠️)

**Only 2 tools currently active**:

#### 1. `list_available_datasets()`
**Location**: `src/mcp/tools/data.py`

Lists CSV files in the `datasets/` folder.

```python
@mcp.tool
@process_tool
async def list_available_datasets() -> str:
    """List all available datasets in the datasets folder."""
    # Returns ToolResponse with dataset names and sizes
```

**Returns**:
```
Summary: "Available datasets (3):
  - sales.csv (12.5 MB)
  - customers.csv (3.2 MB)
  - products.csv (0.8 MB)"
```

#### 2. `tool_description(func_name)`
**Location**: `src/mcp/tools/meta.py`

Returns documentation for a given tool function.

```python
@mcp.tool
@process_tool
def tool_description(func_name: str) -> str:
    """Get the description/docstring of a tool."""
    # Returns tool's docstring
```

**All Other Tools**: Commented out in `src/mcp/server.py` (lines 26-67)

### ToolResponse Model (Implemented ✅)

**Location**: `src/models/tool_response.py`

The core abstraction for handling context window constraints:

```python
class ToolResponse(BaseModel):
    entity_id: str           # Unique identifier (acts as variable name)
    type: str = "tool_response"
    version: int = 1
    created_at: datetime
    updated_at: datetime

    payload: Any            # Actual data (can be stored in MinIO)
    summary: str            # What agent sees (returned to Claude)
    metadata: dict          # Tool execution metadata
    storage_hint: str       # "never" | "session" | "always"
    suggested_name: str     # Human-readable variable name
```

**Key Methods**:
- `from_dict()` - Create from dictionary
- Automatic entity_id generation
- Timestamp management

### Data Science Library (Exists but Not Exposed ⚠️)

**Location**: `src/data_science/`

A complete data science codebase from a previous forecasting project:

**Available but NOT Exposed as MCP Tools**:
- ✅ Database client (`database/client.py`) - Snowflake operations
- ✅ Feature store library (`feature_store/library/`) - 15+ transformations
- ✅ Pipelines (`pipelines/`) - experiment, feature_store, model_selection, hyperparameter_tuning, inference
- ✅ Features (`features/`) - Time series feature implementations
- ✅ Models (`regression/`, `forecast/`) - ML model implementations
- ✅ Snowflake utilities (`snowflake/`) - Session, transaction, Cortex AI
- ✅ Visualizations (`visualizations/`) - Plotting utilities

**These exist but are not callable by the agent yet** - they need to be wrapped as MCP tools.

### Summary of Current State

```
✅ IMPLEMENTED:
   - Infrastructure (Docker Compose with all services)
   - Storage layer (MongoDB + MinIO repositories)
   - ToolResponse model
   - FastMCP server (basic)
   - 2 active MCP tools
   - Data science library code (not exposed)

⚠️ PARTIALLY IMPLEMENTED:
   - Middleware (basic version only)
   - MCP server (no tool variety)

❌ NOT IMPLEMENTED:
   - Most MCP tools (all commented out)
   - Async job execution (Celery)
   - Caching and deduplication
   - Note-taking system
   - Full agent workflow
   - Entity reference resolution
```

---

## The Vision: What's Required

Based on `docs/CONTEXT.md`, this section describes what needs to be implemented to achieve the project's vision.

### Vision Overview

**Goal**: Create an AI-powered data science assistant that can perform end-to-end ML workflows through natural language, solving the context window limitation problem.

**Core Innovation**: The **ToolResponse pattern** - tools return summaries to the agent while storing full results as "variables" (entity_id references) that can be used in subsequent tool calls.

### Required Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude AI Agent                          │
│              (Natural language interface)                   │
└────────────────────┬────────────────────────────────────────┘
                     │ MCP Protocol
                     │
┌────────────────────▼────────────────────────────────────────┐
│               LAYER 1: MCP Tools                            │
│  Complete suite of data science tools across all categories │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              LAYER 2: Middleware                            │
│  • Cache queries to avoid duplicates                        │
│  • Resolve entity_id references                             │
│  • Store tool responses                                     │
│  • Return only summaries to agent                           │
│  • Support async job execution                              │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│             LAYER 3: Infrastructure                         │
│  MongoDB • MinIO • MLflow • Celery • Redis • Snowflake     │
└─────────────────────────────────────────────────────────────┘
```

### Required MCP Tools

All these tools need to be implemented (currently commented out):

#### Data Access Tools
- `load_csv(filename)` - Load CSV from datasets folder
- `load_dataset(entity_id)` - Load previously stored dataset
- `snowflake_query(query)` - Execute Snowflake SQL query
- `download_table(table_path)` - Download table from Snowflake

#### Data Exploration Tools
- `describe_dataset(entity_id)` - Statistical summary
- `profile_data(entity_id)` - Comprehensive data profiling
- `analyze_correlations(entity_id, target)` - Correlation analysis
- `detect_missing_values(entity_id)` - Missing data analysis
- `visualize_distribution(entity_id, column)` - Create distribution plots
- `visualize_timeseries(entity_id, date_col, value_col)` - Time series plots

#### Feature Engineering Tools
- `create_feature_pipeline(config)` - Build feature transformation pipeline
- `apply_transformations(entity_id, transformations)` - Apply transformations to data
- `list_available_transformations()` - Show available feature transformations
- `validate_feature_config(config)` - Validate feature pipeline configuration

#### Modeling Tools
- `submit_training_job(config, async_mode=True)` - Start model training
- `submit_hyperparameter_tuning(config, param_space)` - Optimize hyperparameters
- `train_model_sync(entity_id, model_type, params)` - Synchronous training

#### Job Management Tools
- `get_job_status(job_id)` - Check job status
- `get_job_result(job_id)` - Retrieve completed job results
- `cancel_job(job_id)` - Cancel running job
- `list_jobs(filters)` - List all jobs

#### Model Management Tools
- `register_model(model_id, name)` - Register model in MLflow
- `list_models(experiment_id)` - List all models
- `compare_models(model_ids, metric)` - Compare model performance
- `get_model_details(model_id)` - Get model metadata

#### Deployment Tools
- `create_inference_pipeline(model_id)` - Create deployment pipeline
- `batch_predict(model_id, entity_id)` - Batch predictions
- `deploy_model(model_id, environment)` - Deploy to production

#### Meta Tools
- ✅ `tool_description(func_name)` - Get tool documentation (EXISTS)
- `get_tool_examples(tool_name)` - Get usage examples
- `list_available_tools()` - List all tools

#### Note-Taking Tools (Critical for Vision)
- `create_note(title, content)` - Create new note
- `update_note(note_id, content)` - Update existing note
- `append_to_note(note_id, content)` - Append to note
- `get_note(note_id)` - Retrieve note
- `search_notes(query)` - Search notes
- `list_notes()` - List all notes

### Required Agent Workflow

From CONTEXT.md, the agent should follow this workflow:

#### 1. Assess the Task
```
User: "Build a sales forecasting model"

Agent analyzes:
- What data is available?
- What features might be useful?
- What's the appropriate modeling approach?
- What information is missing?
```

#### 2. Explore Data (Using Tools)
```python
# List available data
datasets = list_available_datasets()
# → entity_id: "tr_001"

# Load data
sales = load_csv("sales.csv")
# → entity_id: "tr_002"
# Agent sees summary only, not full dataset

# Profile the data
profile = profile_data(entity_id="tr_002")
# → entity_id: "tr_003"
# Agent sees: "100K rows, 25 columns, 3 numerical, 22 categorical..."

# Analyze correlations
correlations = analyze_correlations(entity_id="tr_002", target="sales")
# → entity_id: "tr_004"
# Agent sees: "Top correlations: price (0.85), season (0.72)..."

# Create note to track findings
note = create_note(
    title="Sales Forecasting - Data Exploration",
    content="Dataset has 100K rows...\nKey correlations identified..."
)
```

#### 3. Create Pipeline Config
```python
# Agent constructs configuration using domain knowledge
config = {
    "experiment": {
        "experiment_id": "exp_001",
        "use_case_id": "sales_forecast",
        "data": {"training_data": "DB.SCHEMA.SALES"},
        "time_series": {
            "date_column": "date",
            "metrics": {"column": "sales", "aggregation": "sum"}
        }
    },
    "features": {
        "transformations": [
            {"type": "lag", "columns": ["sales"], "lags": [1, 7, 30]},
            {"type": "rolling", "window": 7, "agg": "mean"}
        ]
    },
    "model": {
        "algorithm": "xgboost",
        "hyperparameters": {"n_estimators": 100, "max_depth": 5}
    }
}
```

#### 4. Validate Config
```python
validation = validate_pipeline_config(config=config)
# → entity_id: "tr_005"
# Agent sees: "Configuration valid ✓"
```

#### 5. Submit Job (Async Execution)
```python
job = submit_training_job(config=config, async_mode=True)
# → Returns: {"job_id": "job_xyz789", "status": "SUBMITTED"}
# Agent sees: "Job submitted to Celery worker"

# Update notes
update_note(
    note_id="note_001",
    content="...\\nSubmitted training job: job_xyz789"
)
```

#### 6. Monitor Job
```python
# Poll for completion
while True:
    status = get_job_status(job_id="job_xyz789")
    # → "RUNNING" or "COMPLETED" or "FAILED"
    if status == "COMPLETED":
        break
```

#### 7. Evaluate Results
```python
results = get_job_result(job_id="job_xyz789")
# → entity_id: "tr_006"
# Agent sees: "Model trained: RMSE=145.2, R²=0.89"

# Analyze
analysis = compare_models(
    model_ids=["model_001", "model_002"],
    metric="rmse"
)
# → entity_id: "tr_007"

# Document in notes
append_to_note(
    note_id="note_001",
    content="Results: RMSE=145.2, best model is model_002"
)
```

#### 8. Iterate or Deploy
```python
# Option A: Tune hyperparameters
tuning = submit_hyperparameter_tuning(
    experiment_id="exp_001",
    param_space={
        "n_estimators": [100, 200, 500],
        "max_depth": [5, 10, 15]
    },
    async_mode=True
)

# Option B: Deploy
deployment = deploy_model(
    model_id="model_002",
    environment="production"
)
```

### Required Middleware Enhancements

The middleware needs these capabilities (currently missing):

#### 1. Entity Reference Resolution
```python
# Before calling tool, resolve entity_id to actual data
if "entity_id" in kwargs:
    entity_id = kwargs["entity_id"]
    entity = await registry.get("tool_response", entity_id)
    kwargs["data"] = entity.payload  # Replace entity_id with actual data
```

#### 2. Caching and Deduplication
```python
# Hash tool call
cache_key = hash_tool_call(func_name, args, kwargs)

# Check if already executed
cached = await cache.get(cache_key)
if cached:
    return cached

# Execute and cache
result = await execute_tool(func, args, kwargs)
await cache.set(cache_key, result, ttl=3600)
```

#### 3. Async Job Support
```python
if async_mode:
    # Submit to Celery
    task = celery_app.send_task(
        "tasks.run_tool",
        args=[func_name, args, kwargs]
    )
    return {
        "job_id": task.id,
        "status": "SUBMITTED"
    }
else:
    # Execute synchronously
    return await execute_tool(func, args, kwargs)
```

#### 4. Storage Based on Hint
```python
if tool_response.storage_hint == "always":
    await registry.save(tool_response)
elif tool_response.storage_hint == "session":
    await session_store.save(tool_response, ttl=86400)
# "never" → don't persist
```

### Required Celery Integration

**Location**: `src/workers/` (needs to be created)

```python
# src/workers/celery_app.py
from celery import Celery

app = Celery("maxa-ds-agent", broker="redis://localhost:6379/0")

@app.task(name="tasks.run_tool")
def run_tool(func_name, args, kwargs):
    """Execute a tool asynchronously."""
    # Import and execute tool
    # Log to MLflow
    # Return result
    pass

@app.task(name="tasks.train_model")
def train_model(config):
    """Train a model asynchronously."""
    # Execute pipeline
    # Log to MLflow
    # Store artifacts
    pass
```

**Start worker**:
```bash
celery -A src.workers.celery_app worker --loglevel=info
```

### Required Note-Taking System

**Location**: `src/storage/repositories/notebook.py` (needs to be created)

```python
class Note(BaseModel):
    entity_id: str
    type: str = "note"
    title: str
    content: str  # Markdown
    tags: list[str]
    references: list[str]  # entity_ids of related tool responses
    created_at: datetime
    updated_at: datetime

class NotebookRepository(BaseRepository[Note]):
    # CRUD operations for notes
    pass
```

### Summary of Required Work

To achieve the vision, the following needs to be implemented:

```
HIGH PRIORITY (Core Vision):
1. ✅ Uncomment and activate all existing data science tools
2. ✅ Implement entity_id resolution in middleware
3. ✅ Implement note-taking system (tools + repository)
4. ✅ Implement caching in middleware
5. ✅ Integrate Celery for async jobs
6. ✅ Create job management tools
7. ✅ Wire data science pipelines to MCP tools

MEDIUM PRIORITY (Enhanced Vision):
8. ✅ Add tool usage examples
9. ✅ Improve error messages
10. ✅ Add visualization tools

LOW PRIORITY (Nice to Have):
11. ✅ Session management
12. ✅ MLflow integration in middleware
13. ✅ Advanced caching strategies
```

---

## Potential Improvements

This section covers enhancements beyond the core vision.

### Functional Improvements

#### 1. Advanced Caching Strategies
**Beyond Vision**: ✅
**Priority**: Medium
**Effort**: Medium

**Enhancement over vision**:
- Vision requires basic caching (deduplication)
- This adds: Smart invalidation, TTL policies, cache warming

**Proposal**:
- Semantic caching (similar queries return cached results)
- Cache invalidation when source data changes
- Tiered caching (Redis + in-memory)
- Cache hit rate monitoring

**Benefits**:
- Even faster responses
- Lower infrastructure costs
- Better user experience

#### 2. Interactive Visualizations
**Beyond Vision**: ✅
**Priority**: Medium
**Effort**: High

**Enhancement over vision**:
- Vision has basic visualization tools
- This adds: Interactive Plotly charts, drill-down, export

**Proposal**:
- Generate interactive HTML visualizations
- Store in MinIO, return URLs
- Support zoom, pan, hover tooltips
- Export to PNG/PDF

**Benefits**:
- Better data exploration
- Sharable visualizations
- Professional reporting

#### 3. AutoML Integration
**Beyond Vision**: ✅
**Priority**: Low
**Effort**: Very High

**Enhancement over vision**:
- Vision has manual model selection + hyperparameter tuning
- This adds: Fully automated ML pipeline

**Proposal**:
- Integrate AutoGluon or H2O AutoML
- Automatic feature engineering
- Ensemble generation
- Neural architecture search

**Benefits**:
- Faster time to value
- Better model performance
- Handle complex problems

#### 4. Model Explainability
**Beyond Vision**: ✅
**Priority**: Medium
**Effort**: Medium

**Enhancement over vision**:
- Vision focuses on model performance
- This adds: Understanding *why* models make predictions

**Proposal**:
- SHAP value computation
- Feature importance plots
- Individual prediction explanations
- Counterfactual generation

**Benefits**:
- Build stakeholder trust
- Debug model issues
- Meet regulatory requirements

#### 5. A/B Testing Framework
**Beyond Vision**: ✅
**Priority**: Low
**Effort**: High

**Enhancement over vision**:
- Vision deploys models to production
- This adds: Safe, controlled rollout

**Proposal**:
- Traffic splitting
- Metric collection per variant
- Statistical significance testing
- Automated winner selection

**Benefits**:
- Validate improvements
- Reduce deployment risk
- Optimize business metrics

#### 6. Real-Time Feature Monitoring
**Beyond Vision**: ✅
**Priority**: Low
**Effort**: High

**Enhancement over vision**:
- Vision trains and deploys
- This adds: Production monitoring

**Proposal**:
- Track feature distributions
- Detect data drift
- Alert on anomalies
- Automatic retraining triggers

**Benefits**:
- Prevent model degradation
- Early warning system
- Maintain model quality

#### 7. Collaborative Features
**Beyond Vision**: ✅
**Priority**: Low
**Effort**: High

**Enhancement over vision**:
- Vision is single-user
- This adds: Multi-user collaboration

**Proposal**:
- Share experiments and notes
- Comments on results
- Team workspaces
- Access control

**Benefits**:
- Team productivity
- Knowledge sharing
- Reproducibility

#### 8. Frontend Web UI
**Beyond Vision**: Partial (mentioned in CONTEXT.md as future)
**Priority**: Low
**Effort**: Very High

**Enhancement over vision**:
- Vision is AI-agent interface only
- This adds: Visual, point-and-click interface

**Proposal**:
- React/Vue dashboard
- Experiment tracking UI
- Visual pipeline builder
- Chart gallery
- Admin panel

**Benefits**:
- Serve non-technical users
- Better for presentations
- Alternative interaction mode

### Non-Functional Improvements

#### 1. Comprehensive Testing
**Core Requirement**: ✅ (should be part of vision)
**Priority**: High
**Effort**: High

**Current State**: pytest installed, no tests

**Proposal**:
```
tests/
├── unit/
│   ├── test_tools.py
│   ├── test_middleware.py
│   ├── test_repositories.py
│   └── test_pipelines.py
├── integration/
│   ├── test_end_to_end.py
│   └── test_storage.py
├── fixtures/
│   └── sample_data.py
└── conftest.py
```

**Coverage Target**: 80%+

**Benefits**:
- Prevent regressions
- Faster development
- Documentation via tests

#### 2. Enhanced Observability
**Core Requirement**: ✅ (essential for production)
**Priority**: High
**Effort**: Medium

**Current State**: Basic loguru logging, OpenTelemetry deps installed

**Proposal**:
- Distributed tracing (Jaeger)
- Metrics dashboard (Prometheus + Grafana)
- Structured logging with correlation IDs
- Custom ML metrics (training time, dataset size, etc.)
- Alerting (PagerDuty, Slack)

**Benefits**:
- Debug production issues
- Performance optimization
- Capacity planning

#### 3. Security Hardening
**Core Requirement**: ✅ (essential for production)
**Priority**: High
**Effort**: Medium

**Current State**: Basic auth for MongoDB/MinIO

**Proposal**:
- **Authentication**: OAuth2 for MCP server
- **Authorization**: RBAC for tools (data scientists vs analysts)
- **Encryption**: TLS everywhere, encrypted S3 buckets
- **Secrets**: AWS Secrets Manager / GCP Secret Manager
- **Audit Logging**: Track all tool executions
- **Input Validation**: Prevent SQL injection, code injection
- **Rate Limiting**: Prevent abuse

**Benefits**:
- Protect sensitive data
- Compliance (GDPR, SOC2)
- Prevent abuse

#### 4. Performance Optimization
**Core Requirement**: Partial (basic performance needed)
**Priority**: Medium
**Effort**: Medium

**Proposal**:
- **Async I/O**: Full asyncio adoption
- **Connection Pooling**: Reuse DB connections
- **Batch Processing**: Process multiple datasets
- **Compression**: gzip payloads in MinIO
- **Lazy Loading**: Load data on-demand
- **Query Optimization**: Index MongoDB, optimize Snowflake queries

**Targets**:
- Tool response time: <2s (p95)
- Job submission: <500ms
- Large dataset upload: <30s for 100MB

#### 5. Scalability
**Core Requirement**: Partial (needed as usage grows)
**Priority**: Medium
**Effort**: High

**Proposal**:
- **Horizontal Scaling**: Load balancer + multiple MCP servers
- **Distributed Workers**: Celery on multiple nodes
- **Database Scaling**: MongoDB sharding, read replicas
- **Object Storage**: S3/GCS instead of MinIO
- **Kubernetes**: Container orchestration
- **Auto-scaling**: Scale based on load

**Targets**:
- 100+ concurrent users
- 1000+ tool calls/minute
- 10TB+ artifact storage

#### 6. CI/CD Pipeline
**Core Requirement**: ✅ (essential for sustainable development)
**Priority**: High
**Effort**: Medium

**Proposal**:
```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  lint:
    - ruff check
    - ruff format --check

  test:
    - pytest --cov=src
    - coverage report

  build:
    - docker build
    - docker push to registry

  deploy:
    - deploy to dev (auto)
    - deploy to staging (manual)
    - deploy to prod (manual)
```

**Benefits**:
- Catch bugs early
- Automated deployments
- Consistent quality

#### 7. Configuration Management
**Core Requirement**: Partial
**Priority**: Medium
**Effort**: Low

**Current State**: .env files

**Proposal**:
- Centralized config service (Consul, etcd)
- Environment-specific configs
- Feature flags (LaunchDarkly, Unleash)
- Config validation on startup
- Hot reload for some settings

**Benefits**:
- Easier environment management
- Gradual rollout
- A/B testing infrastructure

#### 8. Disaster Recovery
**Core Requirement**: ✅ (essential for production)
**Priority**: Medium
**Effort**: Medium

**Proposal**:
- **Backups**:
  - MongoDB: Daily dumps to S3
  - MinIO: Replication or sync to S3
  - PostgreSQL: WAL archiving
- **Recovery Procedures**: Documented runbooks
- **DR Drills**: Quarterly testing
- **RTO/RPO**: 4 hours / 24 hours

**Benefits**:
- Business continuity
- Data protection
- Peace of mind

#### 9. Documentation
**Core Requirement**: ✅ (essential for adoption)
**Priority**: High
**Effort**: Medium

**Current State**: README files, CONTEXT.md, ARCHITECTURE.md

**Proposal**:
- **API Docs**: Auto-generated from docstrings (Sphinx)
- **Architecture Diagrams**: Keep updated
- **Runbooks**:
  - Deployment guide
  - Troubleshooting guide
  - Disaster recovery
- **Onboarding**: Developer setup guide
- **ADRs**: Architecture Decision Records
- **Video Tutorials**: Common workflows

**Tools**: MkDocs, Docusaurus, or Sphinx

#### 10. Data Governance
**Core Requirement**: Partial (depends on use case)
**Priority**: Medium
**Effort**: High

**Proposal**:
- **Data Lineage**: Track data flow from source to model
- **Schema Registry**: Version control for schemas
- **Data Quality**: Validation at ingestion
- **Retention Policies**: Auto-delete old data
- **Compliance**:
  - PII detection and masking
  - Right to deletion (GDPR)
  - Audit trails

**Benefits**:
- Regulatory compliance
- Data quality
- Trust and transparency

#### 11. Resource Management
**Core Requirement**: Partial
**Priority**: Medium
**Effort**: Medium

**Proposal**:
- Memory/CPU limits per container
- Job timeout policies
- Storage quotas per user/workspace
- Rate limiting on API calls
- Graceful resource exhaustion handling

**Benefits**:
- Prevent resource hogging
- Cost control
- Stability

### Summary: What's Required vs Improvements

```
┌─────────────────────────────────────────────────────────────┐
│                    CORE VISION                              │
│  (Must implement to achieve CONTEXT.md goals)              │
├─────────────────────────────────────────────────────────────┤
│  1. ✅ All data science tools (currently commented)         │
│  2. ✅ Entity reference resolution                          │
│  3. ✅ Note-taking system                                   │
│  4. ✅ Basic caching (deduplication)                        │
│  5. ✅ Celery for async jobs                               │
│  6. ✅ Job management tools                                │
│  7. ✅ Wire pipelines to MCP tools                         │
│  8. ✅ Testing (unit + integration)                        │
│  9. ✅ Observability (logging, metrics, tracing)           │
│ 10. ✅ Security (auth, encryption, audit logs)             │
│ 11. ✅ CI/CD pipeline                                      │
│ 12. ✅ Documentation                                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              BEYOND VISION (Nice to Have)                   │
├─────────────────────────────────────────────────────────────┤
│  • AutoML integration                                       │
│  • Model explainability (SHAP)                             │
│  • A/B testing framework                                   │
│  • Real-time monitoring                                    │
│  • Interactive visualizations                              │
│  • Frontend web UI                                         │
│  • Advanced caching (semantic)                             │
│  • Collaborative features                                  │
│  • Data governance tools                                   │
│  • Kubernetes deployment                                   │
└─────────────────────────────────────────────────────────────┘
```

## Conclusion

**Current State**: Solid infrastructure foundation with minimal tools (2/50+)

**Path to Vision**:
1. Activate existing tools (uncomment in server.py)
2. Enhance middleware (entity resolution, caching, async)
3. Integrate Celery for async execution
4. Build note-taking system
5. Add comprehensive testing

**Estimated Effort to Vision**: 4-6 weeks (1 developer)

**Beyond Vision**: AutoML, explainability, UI - add as needed based on user feedback

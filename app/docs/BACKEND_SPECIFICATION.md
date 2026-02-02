# Backend Specification - MAXA ML Platform Web API

**Version**: 1.0
**Last Updated**: 2026-01-08
**Purpose**: Detailed specification for FastAPI web server providing REST API access to ML platform capabilities

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [API Design](#api-design)
5. [Authentication & Authorization](#authentication--authorization)
6. [Data Models](#data-models)
7. [API Endpoints](#api-endpoints)
8. [WebSocket Support](#websocket-support)
9. [File Upload/Download](#file-uploaddownload)
10. [Error Handling](#error-handling)
11. [Rate Limiting & Quotas](#rate-limiting--quotas)
12. [Integration with Existing Infrastructure](#integration-with-existing-infrastructure)
13. [Deployment](#deployment)
14. [Monitoring & Logging](#monitoring--logging)

---

## Overview

### Purpose

The MAXA ML Platform Web API is a **FastAPI-based REST service** that provides programmatic access to all ML operations currently available through the MCP server. It enables data scientists to perform experiments, model training, data analysis, and inference through a web interface or API clients.

### Key Goals

1. **Unified Backend**: Share infrastructure (MongoDB, MLflow, Celery, MinIO, Redis) with MCP server
2. **Feature Parity**: All MCP tools accessible via REST API
3. **Real-time Updates**: WebSocket support for job progress, live metrics
4. **Multi-tenancy**: Support multiple users/teams with isolation
5. **Production-ready**: Authentication, rate limiting, audit logging
6. **Developer-friendly**: OpenAPI docs, SDKs, examples

### Non-Goals

- This is NOT a replacement for the MCP server (both coexist)
- NOT a general-purpose data warehouse (uses existing storage)
- NOT a deployment platform (MLflow handles model serving)

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
├────────────────┬────────────────┬───────────────────────────────┤
│  Web Frontend  │  API Clients   │   AI Agent (MCP)              │
│  (React SPA)   │  (Python SDK)  │   (Claude via MCP Server)     │
└────────┬───────┴────────┬───────┴──────────┬────────────────────┘
         │                │                   │
         └────────────────┼───────────────────┘
                          │
         ┌────────────────▼────────────────┐
         │   API Gateway / Load Balancer   │
         │   (nginx/Traefik)                │
         └────────────────┬────────────────┘
                          │
         ┌────────────────▼────────────────┐
         │   FastAPI Web Server             │
         │   (Port 8000)                    │
         ├──────────────────────────────────┤
         │  • REST API Endpoints            │
         │  • WebSocket Endpoints           │
         │  • Authentication Middleware     │
         │  • Rate Limiting                 │
         │  • Request Validation            │
         │  • OpenAPI Documentation         │
         └────────────────┬────────────────┘
                          │
         ┌────────────────▼────────────────────────────┐
         │         Shared Service Layer                │
         ├─────────────────────────────────────────────┤
         │  • Repository Layer (same as MCP)           │
         │  • Business Logic (reuse MCP tool logic)    │
         │  • Job Submission (Celery)                  │
         │  • Event Bus (Redis Pub/Sub)                │
         └────────────────┬────────────────────────────┘
                          │
         ┌────────────────▼────────────────────────────┐
         │         Infrastructure Layer                │
         ├─────────────────────────────────────────────┤
         │  MongoDB  │ MinIO │ MLflow │ Redis │ Celery │
         └─────────────────────────────────────────────┘
```

### Component Responsibilities

**FastAPI Web Server**:
- HTTP REST API endpoints
- WebSocket connections for real-time updates
- Authentication & authorization
- Request validation (Pydantic)
- Response serialization
- Rate limiting & throttling
- CORS handling
- OpenAPI documentation

**Shared Service Layer**:
- Reuse existing repositories from MCP server (`src/storage/repositories/`)
- Reuse business logic from MCP tools (extract to shared modules)
- Event-driven architecture (Redis Pub/Sub for real-time updates)
- Job orchestration (Celery task submission)

**Infrastructure Layer**:
- Same as MCP server (no changes needed)

---

## Technology Stack

### Core Framework

- **FastAPI** (v0.115+): Modern async web framework
- **Pydantic** (v2.0+): Data validation and settings
- **Uvicorn** (v0.32+): ASGI server
- **Python 3.12+**: Runtime

### Authentication & Security

- **JWT (PyJWT)**: Token-based authentication
- **Passlib + Bcrypt**: Password hashing
- **Python-Jose**: JWT utilities
- **FastAPI-Users** (optional): User management framework

### Real-time Communication

- **WebSockets** (FastAPI built-in): Bidirectional communication
- **Redis Pub/Sub**: Event broadcasting
- **SSE** (Server-Sent Events, optional): One-way streaming

### API Documentation

- **OpenAPI 3.1**: API specification (FastAPI auto-generates)
- **Swagger UI**: Interactive API docs (built-in)
- **ReDoc**: Alternative API docs (built-in)

### Testing

- **pytest**: Test framework
- **httpx**: Async HTTP client for testing
- **pytest-asyncio**: Async test support
- **Faker**: Test data generation

### Monitoring

- **Prometheus**: Metrics collection
- **OpenTelemetry**: Distributed tracing
- **Loguru**: Structured logging

---

## API Design

### REST Principles

1. **Resource-based**: URLs represent resources (datasets, jobs, models)
2. **HTTP Methods**: GET (read), POST (create), PUT/PATCH (update), DELETE (remove)
3. **Stateless**: Each request contains all necessary information
4. **HATEOAS**: Include links to related resources

### Versioning Strategy

**URL Path Versioning**:
```
/api/v1/datasets
/api/v2/datasets  # Future version
```

### Response Format

**Standard Success Response**:
```json
{
  "success": true,
  "data": { /* resource data */ },
  "metadata": {
    "timestamp": "2026-01-08T12:00:00Z",
    "request_id": "uuid-here"
  }
}
```

**Standard Error Response**:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid column name",
    "details": {
      "field": "column_name",
      "constraint": "must_exist"
    }
  },
  "metadata": {
    "timestamp": "2026-01-08T12:00:00Z",
    "request_id": "uuid-here"
  }
}
```

### Pagination

**Cursor-based Pagination** (preferred for large datasets):
```
GET /api/v1/datasets?limit=20&cursor=eyJpZCI6MTIzfQ==
```

Response:
```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTQzfQ==",
    "has_more": true,
    "total_count": 1000
  }
}
```

### Filtering & Sorting

**Filtering**:
```
GET /api/v1/datasets?status=completed&created_after=2026-01-01
```

**Sorting**:
```
GET /api/v1/datasets?sort_by=created_at&order=desc
```

### Field Selection (Sparse Fieldsets)

```
GET /api/v1/datasets?fields=id,name,created_at
```

---

## Authentication & Authorization

### Authentication Flow

**JWT-based Authentication**:

1. **User Login**:
   ```
   POST /api/v1/auth/login
   Body: {"email": "user@example.com", "password": "***"}
   Response: {"access_token": "jwt-token", "refresh_token": "refresh-token"}
   ```

2. **Authenticated Requests**:
   ```
   GET /api/v1/datasets
   Header: Authorization: Bearer <jwt-token>
   ```

3. **Token Refresh**:
   ```
   POST /api/v1/auth/refresh
   Body: {"refresh_token": "refresh-token"}
   Response: {"access_token": "new-jwt-token"}
   ```

### User Model

```python
class User(BaseModel):
    id: str
    email: EmailStr
    username: str
    full_name: str
    is_active: bool = True
    is_superuser: bool = False
    organization_id: str
    teams: list[str]
    created_at: datetime
    last_login: datetime | None
```

### Authorization Levels

1. **Public** (no auth): Health checks, documentation
2. **Authenticated**: All API operations
3. **Team-scoped**: Access limited to team resources
4. **Admin**: User management, system settings

### Permissions System

**Resource-based Permissions**:
```python
class Permission(str, Enum):
    READ_DATASET = "dataset:read"
    WRITE_DATASET = "dataset:write"
    DELETE_DATASET = "dataset:delete"
    SUBMIT_JOB = "job:submit"
    READ_JOB = "job:read"
    CANCEL_JOB = "job:cancel"
    READ_MODEL = "model:read"
    DEPLOY_MODEL = "model:deploy"
```

**Role-based Access Control (RBAC)**:
```python
ROLES = {
    "viewer": [Permission.READ_DATASET, Permission.READ_JOB, Permission.READ_MODEL],
    "analyst": [...],  # viewer + submit jobs, create datasets
    "data_scientist": [...],  # analyst + train models, deploy models
    "admin": [...]  # all permissions
}
```

---

## Data Models

### Core Models (Pydantic Schemas)

**Dataset Models**:

```python
# Request schema
class DatasetUploadRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    tags: list[str] = Field(default_factory=list)
    source_type: Literal["csv", "excel", "parquet", "sql"]

# Response schema
class DatasetResponse(BaseModel):
    id: str
    name: str
    description: str | None
    tags: list[str]
    row_count: int
    column_count: int
    columns: list[ColumnInfo]
    size_bytes: int
    created_at: datetime
    created_by: str
    updated_at: datetime
    storage_location: str

class ColumnInfo(BaseModel):
    name: str
    dtype: str
    nullable: bool
    unique_count: int | None
    null_count: int | None
```

**Job Models**:

```python
class JobSubmitRequest(BaseModel):
    job_type: Literal["training", "hpt", "inference", "pipeline"]
    config: dict  # Job-specific configuration
    async_mode: bool = True
    priority: Literal["low", "normal", "high"] = "normal"

class JobResponse(BaseModel):
    id: str
    job_type: str
    status: JobStatus
    config: dict
    result: dict | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    created_by: str
    progress: float | None  # 0.0 to 1.0
    logs: list[str] = []

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

**Model Models**:

```python
class RegisteredModelResponse(BaseModel):
    name: str
    description: str | None
    tags: dict[str, str]
    versions: list[ModelVersionInfo]
    latest_version: int
    created_at: datetime

class ModelVersionInfo(BaseModel):
    version: int
    run_id: str
    stage: Literal["None", "Staging", "Production", "Archived"]
    metrics: dict[str, float]
    params: dict[str, Any]
    created_at: datetime
```

---

## API Endpoints

### 1. Authentication & Users

```
POST   /api/v1/auth/register           # Register new user
POST   /api/v1/auth/login              # Login (get tokens)
POST   /api/v1/auth/refresh            # Refresh access token
POST   /api/v1/auth/logout             # Logout (invalidate tokens)
GET    /api/v1/users/me                # Get current user
PATCH  /api/v1/users/me                # Update current user
GET    /api/v1/users/{user_id}         # Get user (admin only)
GET    /api/v1/users                   # List users (admin only)
```

### 2. Datasets

```
# Upload & Management
POST   /api/v1/datasets/upload         # Upload CSV/Excel/Parquet
POST   /api/v1/datasets/from-sql       # Load from SQL query
GET    /api/v1/datasets                # List datasets
GET    /api/v1/datasets/{id}           # Get dataset metadata
GET    /api/v1/datasets/{id}/preview   # Preview first N rows
GET    /api/v1/datasets/{id}/download  # Download dataset
DELETE /api/v1/datasets/{id}           # Delete dataset
PATCH  /api/v1/datasets/{id}           # Update metadata (name, tags, description)

# Exploration
GET    /api/v1/datasets/{id}/describe  # Statistical summary
GET    /api/v1/datasets/{id}/profile   # Data profiling
GET    /api/v1/datasets/{id}/correlations  # Correlation analysis
GET    /api/v1/datasets/{id}/missing-values  # Missing value analysis

# Transformations
POST   /api/v1/datasets/{id}/transform # Apply transformation
GET    /api/v1/transformations         # List available transformations

# Data Quality
POST   /api/v1/datasets/{id}/validate-schema   # Validate schema
POST   /api/v1/datasets/{id}/check-quality     # Quality checks
POST   /api/v1/datasets/{id}/detect-outliers   # Outlier detection
POST   /api/v1/datasets/{id}/detect-drift      # Data drift detection
```

### 3. Jobs

```
# Job Management
POST   /api/v1/jobs/training           # Submit training job
POST   /api/v1/jobs/hpt                # Submit HPT job
POST   /api/v1/jobs/inference          # Submit batch inference job
POST   /api/v1/jobs/pipeline           # Submit pipeline job
GET    /api/v1/jobs                    # List jobs
GET    /api/v1/jobs/{id}               # Get job details
GET    /api/v1/jobs/{id}/logs          # Get job logs (stream)
DELETE /api/v1/jobs/{id}               # Cancel job
POST   /api/v1/jobs/{id}/retry         # Retry failed job
```

### 4. Models

```
# Model Registry
GET    /api/v1/models                  # List registered models
GET    /api/v1/models/{name}           # Get model details
GET    /api/v1/models/{name}/versions/{version}  # Get model version
POST   /api/v1/models/{name}/versions/{version}/promote  # Promote to stage
DELETE /api/v1/models/{name}           # Delete model
DELETE /api/v1/models/{name}/versions/{version}  # Delete version

# Inference
POST   /api/v1/models/{name}/predict   # Make predictions
POST   /api/v1/models/{name}/batch-predict  # Batch predictions
```

### 5. Experiments (MLflow)

```
GET    /api/v1/experiments             # List experiments
GET    /api/v1/experiments/{id}        # Get experiment details
GET    /api/v1/experiments/{id}/runs   # List runs in experiment
GET    /api/v1/runs/{id}               # Get run details
GET    /api/v1/runs/{id}/metrics       # Get run metrics
GET    /api/v1/runs/{id}/artifacts     # List run artifacts
POST   /api/v1/runs/compare            # Compare multiple runs
POST   /api/v1/runs/search             # Search runs with filters
```

### 6. Visualizations

```
POST   /api/v1/visualizations/feature-importance    # Feature importance plot
POST   /api/v1/visualizations/confusion-matrix      # Confusion matrix
POST   /api/v1/visualizations/residuals             # Residual plots
POST   /api/v1/visualizations/learning-curves       # Learning curves
POST   /api/v1/visualizations/correlation-heatmap   # Correlation heatmap
POST   /api/v1/visualizations/distribution          # Distribution plots
POST   /api/v1/visualizations/roc-curve             # ROC curve
POST   /api/v1/visualizations/pr-curve              # Precision-recall curve
POST   /api/v1/visualizations/partial-dependence    # Partial dependence plots
```

### 7. Statistical Analysis

```
POST   /api/v1/statistics/hypothesis-test    # Hypothesis testing
POST   /api/v1/statistics/ab-test            # A/B test analysis
POST   /api/v1/statistics/confidence-interval  # Confidence intervals
POST   /api/v1/statistics/significance-test  # Significance testing
```

### 8. Model Explainability

```
POST   /api/v1/explainability/shap           # SHAP explanations
POST   /api/v1/explainability/lime           # LIME explanations
POST   /api/v1/explainability/partial-dependence  # PDP
POST   /api/v1/explainability/feature-contributions  # Feature contributions
POST   /api/v1/explainability/explain-prediction  # Comprehensive explanation
```

### 9. Feature Pipelines

```
POST   /api/v1/pipelines/create        # Create feature pipeline
POST   /api/v1/pipelines/{id}/run      # Run feature pipeline
GET    /api/v1/pipelines               # List pipelines
GET    /api/v1/pipelines/{id}          # Get pipeline details
DELETE /api/v1/pipelines/{id}          # Delete pipeline
```

### 10. System & Admin

```
GET    /api/v1/health                  # Health check
GET    /api/v1/metrics                 # Prometheus metrics
GET    /api/v1/status                  # System status
GET    /api/v1/version                 # API version
GET    /docs                           # Swagger UI
GET    /redoc                          # ReDoc UI
```

---

## WebSocket Support

### Connection

```javascript
// Client connects to WebSocket
const ws = new WebSocket('ws://localhost:8000/api/v1/ws?token=<jwt-token>');
```

### Event Types

**Job Progress Updates**:
```json
{
  "event": "job:progress",
  "data": {
    "job_id": "job-123",
    "status": "running",
    "progress": 0.65,
    "message": "Trial 65/100 completed"
  }
}
```

**Job Completion**:
```json
{
  "event": "job:completed",
  "data": {
    "job_id": "job-123",
    "status": "completed",
    "result": { /* job result */ }
  }
}
```

**Live Metrics (Training)**:
```json
{
  "event": "metrics:update",
  "data": {
    "job_id": "job-123",
    "metrics": {
      "loss": 0.234,
      "accuracy": 0.95
    },
    "step": 1000
  }
}
```

**System Notifications**:
```json
{
  "event": "system:notification",
  "data": {
    "type": "info",
    "message": "Model deployment completed",
    "timestamp": "2026-01-08T12:00:00Z"
  }
}
```

### Client-to-Server Messages

**Subscribe to Job**:
```json
{
  "action": "subscribe",
  "resource": "job",
  "id": "job-123"
}
```

**Unsubscribe**:
```json
{
  "action": "unsubscribe",
  "resource": "job",
  "id": "job-123"
}
```

---

## File Upload/Download

### Upload Endpoints

**Multipart Form Upload**:
```python
@router.post("/datasets/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(None),
    tags: str = Form("[]"),  # JSON array as string
    current_user: User = Depends(get_current_user)
):
    # Stream file to MinIO
    # Create dataset entity in MongoDB
    # Return dataset metadata
```

**Chunked Upload (Large Files)**:
```
POST /api/v1/uploads/init        # Initialize upload, get upload_id
PUT  /api/v1/uploads/{id}/chunk  # Upload chunk
POST /api/v1/uploads/{id}/complete  # Finalize upload
```

### Download Endpoints

**Direct Download**:
```python
@router.get("/datasets/{id}/download")
async def download_dataset(
    id: str,
    format: Literal["csv", "parquet", "excel"] = "csv",
    current_user: User = Depends(get_current_user)
):
    # Stream from MinIO
    return StreamingResponse(
        file_stream,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
```

**Presigned URLs (for large files)**:
```python
@router.get("/datasets/{id}/download-url")
async def get_download_url(id: str):
    # Generate MinIO presigned URL (valid for 1 hour)
    return {"url": presigned_url, "expires_at": expiry_time}
```

---

## Error Handling

### Error Codes

```python
class ErrorCode(str, Enum):
    # Authentication errors (40x)
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"

    # Validation errors (422)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"

    # Resource errors (404)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    DATASET_NOT_FOUND = "DATASET_NOT_FOUND"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"

    # Business logic errors (400)
    INVALID_OPERATION = "INVALID_OPERATION"
    JOB_ALREADY_COMPLETED = "JOB_ALREADY_COMPLETED"

    # Server errors (500)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    STORAGE_ERROR = "STORAGE_ERROR"
    WORKER_ERROR = "WORKER_ERROR"
```

### Exception Handlers

```python
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": false,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors()
            }
        }
    )
```

---

## Rate Limiting & Quotas

### Rate Limits

**Per-User Rate Limits**:
```
- Anonymous: 100 requests/hour
- Authenticated: 1000 requests/hour
- Premium: 10000 requests/hour
```

**Per-Endpoint Rate Limits**:
```
- /datasets/upload: 10 uploads/hour
- /jobs/training: 50 jobs/day
- /jobs/hpt: 20 jobs/day
```

### Quota System

**Resource Quotas**:
```python
class UserQuota(BaseModel):
    max_datasets: int = 100
    max_dataset_size_gb: float = 10.0
    max_concurrent_jobs: int = 5
    max_models: int = 50
    max_storage_gb: float = 50.0
```

**Quota Headers**:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1641024000
```

---

## Integration with Existing Infrastructure

### Shared Components

**1. Repository Layer**:
```python
# Reuse existing repositories
from src.storage.repositories.registry import get_repository_registry

registry = get_repository_registry()
dataset_repo = await registry.get("tool_response", "dataset-123")
```

**2. Business Logic**:
```python
# Extract MCP tool logic into shared modules
from src.services.training import run_training  # Refactored from workers
from src.services.inference import make_predictions

# Use in both MCP tools and API endpoints
```

**3. Celery Workers**:
```python
# Submit jobs to same Celery workers
from src.workers.tasks import train_model

result = train_model.apply_async(args=[config])
```

**4. Event Bus**:
```python
# Publish events to Redis for WebSocket clients
await redis.publish("job:progress", json.dumps(event_data))
```

### Code Organization

```
src/
├── api/                    # NEW: FastAPI web server
│   ├── __init__.py
│   ├── main.py            # FastAPI app entry point
│   ├── dependencies.py    # Dependency injection
│   ├── middleware/        # Auth, CORS, logging
│   ├── routers/           # API endpoints by domain
│   │   ├── auth.py
│   │   ├── datasets.py
│   │   ├── jobs.py
│   │   ├── models.py
│   │   ├── experiments.py
│   │   └── ...
│   ├── schemas/           # Pydantic request/response models
│   ├── websockets/        # WebSocket handlers
│   └── utils/             # Helpers
├── services/              # NEW: Shared business logic
│   ├── training.py        # Refactored from workers
│   ├── inference.py
│   ├── data_processing.py
│   └── ...
├── mcp/                   # EXISTING: MCP server (unchanged)
├── workers/               # EXISTING: Celery workers (unchanged)
├── storage/               # EXISTING: Repositories (unchanged)
├── models/                # EXISTING: Data models (shared)
└── utils/                 # EXISTING: Utilities (shared)
```

---

## Deployment

### Docker Configuration

**New `Dockerfile.api`**:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install -e .

COPY src/ ./src/

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Updated `docker-compose.yaml`**:
```yaml
services:
  # Existing services...

  api_server:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    container_name: api_server
    ports:
      - "8000:8000"
    environment:
      - MONGO_HOST=mongodb
      - REDIS_URL=redis://redis:6379
      - MLFLOW_TRACKING_URI=http://mlflow_server:5000
      - MINIO_ENDPOINT=mlflow_minio:9000
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    depends_on:
      - mongodb
      - redis
      - mlflow_server
    volumes:
      - ../src:/app/src
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Environment Variables

```bash
# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Security
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:3000,https://app.example.com

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100
```

---

## Monitoring & Logging

### Prometheus Metrics

**Custom Metrics**:
```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
http_requests_total = Counter(
    "api_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

# Job metrics
jobs_submitted = Counter("api_jobs_submitted_total", "Jobs submitted", ["type"])
jobs_running = Gauge("api_jobs_running", "Currently running jobs", ["type"])

# Dataset metrics
dataset_uploads = Counter("api_dataset_uploads_total", "Dataset uploads")
dataset_size_bytes = Histogram("api_dataset_size_bytes", "Dataset size")
```

### Structured Logging

```python
from loguru import logger

logger.add(
    "logs/api.log",
    format="{time} | {level} | {extra[request_id]} | {message}",
    rotation="500 MB",
    retention="30 days",
    level="INFO"
)

# Log with context
logger.bind(
    request_id=request.state.request_id,
    user_id=current_user.id
).info("Dataset uploaded", dataset_id=dataset_id)
```

### Distributed Tracing

```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Auto-instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

# Manual spans
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("process_dataset"):
    # Processing logic
    pass
```

---

## Security Considerations

### Authentication Security

1. **Password Requirements**: Min 8 chars, uppercase, lowercase, number, special char
2. **Password Hashing**: Bcrypt with salt
3. **Token Security**:
   - Short-lived access tokens (30 min)
   - Long-lived refresh tokens (7 days)
   - Token rotation on refresh
4. **Session Management**: Store refresh tokens in secure HTTP-only cookies
5. **Rate Limiting**: Brute force protection on login endpoint

### API Security

1. **HTTPS Only**: Enforce TLS in production
2. **CORS**: Whitelist specific origins
3. **CSRF Protection**: For cookie-based auth
4. **Input Validation**: Pydantic validation + sanitization
5. **SQL Injection**: Use parameterized queries (handled by Motor/SQLAlchemy)
6. **File Upload Security**:
   - Validate file types (magic number check)
   - Scan for malware (ClamAV integration)
   - Size limits
   - Quarantine suspicious files

### Data Security

1. **Encryption at Rest**: MinIO server-side encryption
2. **Encryption in Transit**: TLS for all connections
3. **Access Control**: Row-level security (user can only see own datasets)
4. **Audit Logging**: Log all data access and modifications
5. **Data Retention**: Automated cleanup of old datasets/jobs

---

## Performance Optimization

### Caching Strategy

**Redis Caching**:
```python
# Cache expensive computations
@cache(expire=3600)
async def get_dataset_statistics(dataset_id: str):
    # Compute stats
    return stats

# Cache invalidation
await cache.delete(f"dataset:stats:{dataset_id}")
```

**HTTP Caching**:
```python
@router.get("/datasets/{id}")
async def get_dataset(id: str, response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    response.headers["ETag"] = generate_etag(dataset)
    return dataset
```

### Database Optimization

1. **Indexes**: Add indexes on frequently queried fields
2. **Connection Pooling**: Reuse database connections
3. **Query Optimization**: Use projections to fetch only needed fields
4. **Batch Operations**: Bulk insert/update when possible

### Async Processing

1. **Background Tasks**: Use FastAPI BackgroundTasks for non-blocking ops
2. **Streaming Responses**: Stream large responses to reduce memory
3. **Connection Pooling**: HTTP client connection pooling

---

## Testing Strategy

### Test Pyramid

```
    /\
   /  \    E2E Tests (10%)
  /____\
  /    \   Integration Tests (30%)
 /______\
/        \  Unit Tests (60%)
/__________\
```

### Test Categories

**Unit Tests**:
```python
# Test individual functions
async def test_validate_dataset_schema():
    schema = {...}
    result = validate_schema(dataset, schema)
    assert result.valid == True
```

**Integration Tests**:
```python
# Test API endpoints with test database
async def test_upload_dataset_endpoint(client: AsyncClient):
    response = await client.post(
        "/api/v1/datasets/upload",
        files={"file": ("test.csv", csv_data)},
        data={"name": "Test Dataset"}
    )
    assert response.status_code == 200
```

**E2E Tests**:
```python
# Test complete workflows
async def test_training_workflow():
    # Upload dataset
    dataset = await upload_dataset()
    # Submit training job
    job = await submit_training_job(dataset.id)
    # Wait for completion
    await wait_for_job(job.id)
    # Verify model registered
    model = await get_model(job.model_name)
    assert model is not None
```

---

## API Documentation

### OpenAPI Specification

FastAPI auto-generates OpenAPI 3.1 spec with:
- All endpoints documented
- Request/response schemas
- Authentication requirements
- Example requests/responses

**Access Documentation**:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### API Client SDKs

**Auto-generate SDKs**:
```bash
# Python SDK
openapi-generator-cli generate -i openapi.json -g python -o sdk/python

# JavaScript SDK
openapi-generator-cli generate -i openapi.json -g javascript -o sdk/js

# TypeScript SDK
openapi-generator-cli generate -i openapi.json -g typescript-axios -o sdk/ts
```

---

## Versioning & Compatibility

### Semantic Versioning

- **Major**: Breaking changes (v1 → v2)
- **Minor**: New features, backward compatible
- **Patch**: Bug fixes

### Deprecation Policy

1. Announce deprecation in v1.5
2. Mark as deprecated in docs (v1.6)
3. Remove in next major version (v2.0)
4. Provide migration guide

### Backward Compatibility

- Old API versions supported for 6 months after new version release
- Use content negotiation or URL versioning
- Maintain separate routers per API version

---

## Future Enhancements

### Phase 1 (MVP)
- Authentication & basic CRUD endpoints
- Dataset upload/management
- Job submission & monitoring
- Model registry access

### Phase 2
- WebSocket real-time updates
- Advanced visualizations
- Statistical analysis endpoints
- Model explainability

### Phase 3
- GraphQL API (alternative to REST)
- Webhooks for event notifications
- API marketplace (share datasets/models)
- Collaborative features (comments, sharing)

### Phase 4
- Multi-cloud deployment
- Edge deployment support
- Federated learning APIs
- AutoML integration

---

## Success Metrics

### Performance KPIs
- API response time: p95 < 500ms
- WebSocket latency: < 100ms
- Uptime: 99.9%
- Error rate: < 0.1%

### Usage KPIs
- Daily active users
- API requests per day
- Jobs submitted per day
- Models deployed per week

### Business KPIs
- User satisfaction (NPS)
- Time to first model
- Experiment velocity (experiments/week)
- Model deployment frequency

---

**End of Backend Specification**

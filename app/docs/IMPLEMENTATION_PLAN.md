# Implementation Plan: Core Vision

This document provides a detailed, step-by-step plan to implement the core vision described in ARCHITECTURE.md and CONTEXT.md.

## Table of Contents
1. [Overview](#overview)
2. [Phases](#phases)
3. [Detailed Tasks](#detailed-tasks)
4. [Testing Strategy](#testing-strategy)
5. [Deployment Plan](#deployment-plan)
6. [Success Criteria](#success-criteria)

---

## Overview

### Goal
Transform the current minimal MCP server (2 tools) into a fully functional AI-powered data science assistant capable of end-to-end ML workflows.

### Timeline
**Estimated Duration**: 6 weeks (1 developer, full-time)

### Phases
1. **Phase 0: Setup & Foundation** (3 days)
2. **Phase 1: Core Infrastructure** (1 week)
3. **Phase 2: Data Access & Exploration** (1 week)
4. **Phase 3: Feature Engineering & Modeling** (1.5 weeks)
5. **Phase 4: Async Jobs & Orchestration** (1 week)
6. **Phase 5: Note-Taking & Meta Tools** (3 days)
7. **Phase 6: Testing & Documentation** (1 week)
8. **Phase 7: Observability & Security** (4 days)

### Dependencies

```
Phase 0 (Setup)
    ↓
Phase 1 (Infrastructure)
    ↓
Phase 2 (Data Tools) ←─┐
    ↓                   │
Phase 3 (ML Tools)      │
    ↓                   │
Phase 4 (Async Jobs) ───┘
    ↓
Phase 5 (Notes)
    ↓
Phase 6 (Testing)
    ↓
Phase 7 (Observability)
```

---

## Phase 0: Setup & Foundation (3 days)

### Objectives
- Set up development environment
- Create project structure for new components
- Establish coding standards
- Set up initial testing infrastructure

### Tasks

#### Task 0.1: Development Environment Setup
**Effort**: 0.5 days
**Priority**: Critical

**Steps**:
1. Verify all Docker services start correctly:
   ```bash
   cd docker && docker compose up -d
   docker compose ps  # All should be "healthy"
   ```

2. Add Redis service to `docker-compose.yaml`:
   ```yaml
   redis:
     restart: always
     image: redis:alpine
     container_name: redis
     ports:
       - "${REDIS_PORT-6379}:6379"
     networks:
       - backend
     healthcheck:
       test: ["CMD", "redis-cli", "ping"]
       interval: 5s
       timeout: 5s
       retries: 3
   ```

3. Update dependencies in `pyproject.toml`:
   ```toml
   celery = {extras = ["redis"], version = ">=5.4.0,<6.0.0"}
   redis = {extras = ["hiredis"], version = ">=5.0.0,<6.0.0"}
   pytest-asyncio = ">=0.23.0,<1.0.0"
   pytest-cov = ">=4.1.0,<5.0.0"
   ```

4. Install dependencies:
   ```bash
   poetry install
   ```

**Deliverables**:
- ✅ All Docker services running
- ✅ Redis service added
- ✅ Dependencies updated

#### Task 0.2: Project Structure
**Effort**: 0.5 days
**Priority**: Critical

**Steps**:
1. Create directory structure:
   ```bash
   mkdir -p src/workers
   mkdir -p src/mcp/tools/{data_access,exploration,transformation,modeling,deployment,jobs,notes}
   mkdir -p tests/{unit,integration,fixtures}
   mkdir -p docs/runbooks
   ```

2. Create placeholder files:
   ```bash
   touch src/workers/__init__.py
   touch src/workers/celery_app.py
   touch src/workers/tasks.py
   touch tests/conftest.py
   touch tests/__init__.py
   ```

**Deliverables**:
- ✅ Directory structure created
- ✅ Placeholder files in place

#### Task 0.3: Testing Infrastructure
**Effort**: 1 day
**Priority**: High

**Steps**:
1. Create `tests/conftest.py`:
   ```python
   import pytest
   import asyncio
   from motor.motor_asyncio import AsyncIOMotorClient
   from src.storage.backends.document_store import MongoDBDocumentStore
   from src.storage.backends.object_store import MinIOObjectStore
   from src.storage.repositories.registry import RepositoryRegistry

   @pytest.fixture(scope="session")
   def event_loop():
       """Create event loop for async tests."""
       loop = asyncio.get_event_loop_policy().new_event_loop()
       yield loop
       loop.close()

   @pytest.fixture
   async def mongo_client():
       """MongoDB client for testing."""
       client = AsyncIOMotorClient("mongodb://admin:admin@localhost:27017")
       yield client
       client.close()

   @pytest.fixture
   async def doc_store(mongo_client):
       """Document store for testing."""
       return MongoDBDocumentStore(client=mongo_client, db_name="test_db")

   @pytest.fixture
   async def obj_store():
       """Object store for testing."""
       return MinIOObjectStore(
           endpoint="localhost:9000",
           access_key="minioadmin",
           secret_key="minioadmin",
           secure=False
       )

   @pytest.fixture
   async def registry(doc_store, obj_store):
       """Repository registry for testing."""
       reg = RepositoryRegistry(
           document_store=doc_store,
           object_store=obj_store
       )
       await reg.initialize()
       return reg
   ```

2. Create `pytest.ini`:
   ```ini
   [pytest]
   testpaths = tests
   python_files = test_*.py
   python_classes = Test*
   python_functions = test_*
   asyncio_mode = auto
   markers =
       unit: Unit tests
       integration: Integration tests
       slow: Slow running tests
   ```

3. Create first test `tests/unit/test_storage.py`:
   ```python
   import pytest
   from src.models.tool_response import ToolResponse

   @pytest.mark.unit
   async def test_tool_response_creation():
       """Test ToolResponse can be created."""
       tr = ToolResponse(
           payload={"data": [1, 2, 3]},
           summary="Test summary",
           metadata={},
           storage_hint="never"
       )
       assert tr.entity_id is not None
       assert tr.type == "tool_response"
       assert tr.summary == "Test summary"
   ```

4. Run tests:
   ```bash
   pytest tests/ -v
   ```

**Deliverables**:
- ✅ `conftest.py` with fixtures
- ✅ `pytest.ini` configuration
- ✅ First passing test
- ✅ Test command works

#### Task 0.4: CI/CD Pipeline
**Effort**: 1 day
**Priority**: High

**Steps**:
1. Create `.github/workflows/ci.yml`:
   ```yaml
   name: CI

   on:
     push:
       branches: [main, develop]
     pull_request:
       branches: [main, develop]

   jobs:
     lint:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
           with:
             python-version: '3.12'
         - name: Install dependencies
           run: |
             pip install poetry
             poetry install
         - name: Run ruff
           run: |
             poetry run ruff check .
             poetry run ruff format --check .

     test:
       runs-on: ubuntu-latest
       services:
         mongodb:
           image: mongo:latest
           env:
             MONGO_INITDB_ROOT_USERNAME: admin
             MONGO_INITDB_ROOT_PASSWORD: admin
           ports:
             - 27017:27017
         minio:
           image: minio/minio
           env:
             MINIO_ROOT_USER: minioadmin
             MINIO_ROOT_PASSWORD: minioadmin
           ports:
             - 9000:9000
           options: --health-cmd "curl -f http://localhost:9000/minio/health/live"
         redis:
           image: redis:alpine
           ports:
             - 6379:6379

       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
           with:
             python-version: '3.12'
         - name: Install dependencies
           run: |
             pip install poetry
             poetry install
         - name: Run tests
           run: |
             poetry run pytest tests/ -v --cov=src --cov-report=xml
         - name: Upload coverage
           uses: codecov/codecov-action@v3
           with:
             files: ./coverage.xml

     build:
       runs-on: ubuntu-latest
       needs: [lint, test]
       steps:
         - uses: actions/checkout@v3
         - name: Build Docker image
           run: |
             docker build -f docker/Dockerfile.mcp -t mcp-server:${{ github.sha }} .
   ```

2. Create `.github/workflows/deploy.yml` (manual trigger):
   ```yaml
   name: Deploy

   on:
     workflow_dispatch:
       inputs:
         environment:
           description: 'Environment to deploy to'
           required: true
           type: choice
           options:
             - dev
             - staging
             - production

   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - name: Deploy to ${{ github.event.inputs.environment }}
           run: |
             echo "Deploying to ${{ github.event.inputs.environment }}"
             # Add deployment steps here
   ```

**Deliverables**:
- ✅ CI pipeline configured
- ✅ Linting runs on every push
- ✅ Tests run with coverage
- ✅ Docker build step

---

## Phase 1: Core Infrastructure (1 week)

### Objectives
- Enhance middleware with entity resolution and caching
- Set up Celery workers
- Create job management infrastructure

### Tasks

#### Task 1.1: Enhanced Middleware - Entity Resolution
**Effort**: 2 days
**Priority**: Critical

**Steps**:
1. Update `src/mcp/middleware.py`:
   ```python
   import inspect
   from typing import Any, get_type_hints
   from src.storage.repositories.registry import get_repository_registry

   async def resolve_entity_references(func: Callable, kwargs: dict) -> dict:
       """Resolve entity_id references to actual data."""
       registry = get_repository_registry()
       resolved_kwargs = kwargs.copy()

       # Get function signature
       sig = inspect.signature(func)
       type_hints = get_type_hints(func)

       for param_name, param_value in kwargs.items():
           # Check if parameter is named entity_id or ends with _entity_id
           if param_name == "entity_id" or param_name.endswith("_entity_id"):
               if isinstance(param_value, str) and param_value.startswith("tr_"):
                   # Resolve entity_id to actual ToolResponse
                   entity = await registry.get("tool_response", param_value)
                   if entity:
                       # Replace entity_id with payload
                       resolved_kwargs[param_name.replace("_entity_id", "")] = entity.payload
                       resolved_kwargs[f"{param_name}_resolved"] = entity
                   else:
                       raise ValueError(f"Entity not found: {param_value}")

       return resolved_kwargs

   def process_tool(func: Callable) -> Callable:
       """Process tool result for MCP."""

       @functools.wraps(func)
       @timing
       async def wrapper(*args, context: Any = None, **kwargs) -> Any:
           try:
               logger.info(f"Tool Call [START]: {func.__name__}")

               # 1. Resolve entity_id references
               resolved_kwargs = await resolve_entity_references(func, kwargs)

               # 2. Execute tool
               result: ToolResponse = await _call_tool(func, *args, **resolved_kwargs)

               # 3. Save based on storage_hint
               registry = get_repository_registry()
               if result.storage_hint in ["always", "session"]:
                   await registry.save(result)
                   logger.info(f"Saved tool response: {result.entity_id}")

               logger.info(f"Tool Call [END]: {func.__name__}")

               # 4. Return only summary to agent
               return result.summary

           except Exception as e:
               logger.exception(f"Error in tool {func.__name__}: {e}")
               return ToolResponse(
                   payload=None,
                   summary=f"Error in tool {func.__name__}: {str(e)}",
                   metadata={"error": str(e), "tool": func.__name__},
                   storage_hint="never",
               ).summary

       return wrapper
   ```

2. Create tests in `tests/unit/test_middleware.py`:
   ```python
   import pytest
   from src.models.tool_response import ToolResponse
   from src.mcp.middleware import process_tool, resolve_entity_references

   @pytest.mark.unit
   async def test_entity_resolution(registry):
       """Test entity_id gets resolved to payload."""
       # Create and save a tool response
       tr = ToolResponse(
           payload={"data": [1, 2, 3]},
           summary="Test data",
           metadata={},
           storage_hint="always"
       )
       await registry.save(tr)

       # Mock function
       async def mock_tool(data=None):
           return data

       # Resolve entity_id
       kwargs = {"entity_id": tr.entity_id}
       resolved = await resolve_entity_references(mock_tool, kwargs)

       assert "data" in resolved
       assert resolved["data"] == {"data": [1, 2, 3]}
   ```

**Deliverables**:
- ✅ Entity resolution implemented
- ✅ Tests passing
- ✅ Documentation updated

#### Task 1.2: Enhanced Middleware - Caching
**Effort**: 2 days
**Priority**: High

**Steps**:
1. Create `src/utils/cache.py`:
   ```python
   import hashlib
   import json
   from typing import Any
   from redis.asyncio import Redis

   class ToolCache:
       def __init__(self, redis_url: str = "redis://localhost:6379/0"):
           self.redis = Redis.from_url(redis_url, decode_responses=False)

       def _hash_call(self, func_name: str, args: tuple, kwargs: dict) -> str:
           """Generate deterministic hash for tool call."""
           call_data = {
               "func": func_name,
               "args": args,
               "kwargs": sorted(kwargs.items())
           }
           call_str = json.dumps(call_data, sort_keys=True, default=str)
           return hashlib.sha256(call_str.encode()).hexdigest()

       async def get(self, func_name: str, args: tuple, kwargs: dict) -> str | None:
           """Get cached result if exists."""
           cache_key = self._hash_call(func_name, args, kwargs)
           result = await self.redis.get(f"tool_cache:{cache_key}")
           return result.decode() if result else None

       async def set(
           self,
           func_name: str,
           args: tuple,
           kwargs: dict,
           result: str,
           ttl: int = 3600
       ) -> None:
           """Cache tool result."""
           cache_key = self._hash_call(func_name, args, kwargs)
           await self.redis.setex(f"tool_cache:{cache_key}", ttl, result)

       async def invalidate(self, func_name: str) -> None:
           """Invalidate all cache entries for a tool."""
           pattern = f"tool_cache:*"
           async for key in self.redis.scan_iter(match=pattern):
               await self.redis.delete(key)

       async def close(self):
           """Close Redis connection."""
           await self.redis.close()
   ```

2. Update middleware to use cache:
   ```python
   from src.utils.cache import ToolCache

   # Module-level cache instance
   _cache: ToolCache | None = None

   def get_cache() -> ToolCache:
       global _cache
       if _cache is None:
           _cache = ToolCache()
       return _cache

   def process_tool(func: Callable, cacheable: bool = True) -> Callable:
       """Process tool result for MCP."""

       @functools.wraps(func)
       @timing
       async def wrapper(*args, context: Any = None, **kwargs) -> Any:
           try:
               logger.info(f"Tool Call [START]: {func.__name__}")

               # 1. Check cache
               cache = get_cache()
               if cacheable:
                   cached_result = await cache.get(func.__name__, args, kwargs)
                   if cached_result:
                       logger.info(f"Cache hit for {func.__name__}")
                       return cached_result

               # 2. Resolve entity_id references
               resolved_kwargs = await resolve_entity_references(func, kwargs)

               # 3. Execute tool
               result: ToolResponse = await _call_tool(func, *args, **resolved_kwargs)

               # 4. Save based on storage_hint
               registry = get_repository_registry()
               if result.storage_hint in ["always", "session"]:
                   await registry.save(result)
                   logger.info(f"Saved tool response: {result.entity_id}")

               # 5. Cache result
               if cacheable:
                   await cache.set(func.__name__, args, kwargs, result.summary)

               logger.info(f"Tool Call [END]: {func.__name__}")

               # 6. Return only summary to agent
               return result.summary

           except Exception as e:
               logger.exception(f"Error in tool {func.__name__}: {e}")
               return ToolResponse(
                   payload=None,
                   summary=f"Error in tool {func.__name__}: {str(e)}",
                   metadata={"error": str(e), "tool": func.__name__},
                   storage_hint="never",
               ).summary

       return wrapper
   ```

**Deliverables**:
- ✅ Cache implementation
- ✅ Cache integration in middleware
- ✅ Tests for caching

#### Task 1.3: Celery Setup
**Effort**: 2 days
**Priority**: Critical

**Steps**:
1. Create `src/workers/celery_app.py`:
   ```python
   import os
   from celery import Celery

   # Create Celery app
   app = Celery(
       "maxa-ds-agent",
       broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
       backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
   )

   # Configure
   app.conf.update(
       task_serializer="json",
       accept_content=["json"],
       result_serializer="json",
       timezone="UTC",
       enable_utc=True,
       task_track_started=True,
       task_time_limit=3600,  # 1 hour
       task_soft_time_limit=3300,  # 55 minutes
       worker_prefetch_multiplier=1,
       worker_max_tasks_per_child=50,
   )

   # Auto-discover tasks
   app.autodiscover_tasks(["src.workers"])
   ```

2. Create `src/workers/tasks.py`:
   ```python
   from celery import Task
   from src.workers.celery_app import app
   from loguru import logger

   class CallbackTask(Task):
       """Base task with callbacks."""

       def on_success(self, retval, task_id, args, kwargs):
           logger.info(f"Task {task_id} succeeded")

       def on_failure(self, exc, task_id, args, kwargs, einfo):
           logger.error(f"Task {task_id} failed: {exc}")

       def on_retry(self, exc, task_id, args, kwargs, einfo):
           logger.warning(f"Task {task_id} retrying: {exc}")

   @app.task(base=CallbackTask, bind=True, name="tasks.run_tool")
   def run_tool(self, func_name: str, args: tuple, kwargs: dict):
       """Execute a tool asynchronously."""
       logger.info(f"Running tool {func_name} with args={args}, kwargs={kwargs}")

       # Import tool function
       from src.mcp.tools import get_tool_function

       tool_func = get_tool_function(func_name)

       # Execute
       import asyncio
       result = asyncio.run(tool_func(*args, **kwargs))

       return result

   @app.task(base=CallbackTask, bind=True, name="tasks.train_model")
   def train_model(self, config: dict):
       """Train a model asynchronously."""
       logger.info(f"Training model with config: {config}")

       # Import pipeline
       from src.data_science.pipelines.model_selection import model_selection
       from src.data_science.database.client import DBClient

       db_client = DBClient()

       # Execute pipeline
       result = model_selection(config, db_client)

       return result
   ```

3. Create start script `scripts/start_worker.sh`:
   ```bash
   #!/bin/bash
   celery -A src.workers.celery_app worker \
       --loglevel=info \
       --concurrency=2 \
       --max-tasks-per-child=50
   ```

4. Add to `docker-compose.yaml`:
   ```yaml
   celery_worker:
     restart: always
     build:
       context: ../
       dockerfile: docker/Dockerfile.mcp
     image: mcp_server
     container_name: celery_worker
     networks:
       - backend
     environment:
       - REDIS_URL=redis://redis:6379/0
       - MONGO_USER=${MONGO_USER-admin}
       - MONGO_PASSWORD=${MONGO_PASSWORD-admin}
       - MONGO_HOST=mongodb
       - MONGO_PORT=27017
       - MONGO_DB=${MONGO_DATABASE-maxa_ds}
     command: ["celery", "-A", "src.workers.celery_app", "worker", "--loglevel=info"]
     depends_on:
       - redis
       - mongodb
   ```

**Deliverables**:
- ✅ Celery app configured
- ✅ Task definitions
- ✅ Worker container in docker-compose
- ✅ Start script

#### Task 1.4: Job Management Infrastructure
**Effort**: 1 day
**Priority**: High

**Steps**:
1. Create `src/models/job.py`:
   ```python
   from datetime import datetime
   from enum import Enum
   from pydantic import BaseModel, Field
   from typing import Any

   class JobStatus(str, Enum):
       PENDING = "PENDING"
       STARTED = "STARTED"
       RETRY = "RETRY"
       RUNNING = "RUNNING"
       SUCCESS = "SUCCESS"
       FAILURE = "FAILURE"
       REVOKED = "REVOKED"

   class Job(BaseModel):
       entity_id: str = Field(default_factory=lambda: f"job_{uuid.uuid4().hex[:12]}")
       type: str = "job"
       version: int = 1
       created_at: datetime = Field(default_factory=datetime.utcnow)
       updated_at: datetime = Field(default_factory=datetime.utcnow)

       celery_task_id: str
       task_name: str
       args: tuple = ()
       kwargs: dict = {}
       status: JobStatus = JobStatus.PENDING
       result: Any = None
       error: str | None = None
       started_at: datetime | None = None
       completed_at: datetime | None = None
   ```

2. Create `src/storage/repositories/job.py`:
   ```python
   from src.models.job import Job
   from src.storage.repositories.base import BaseRepository
   from src.storage.interfaces import DocumentStore

   class JobRepository(BaseRepository[Job]):
       def __init__(self, document_store: DocumentStore):
           self.doc_store = document_store
           self.collection = "jobs"

       async def save(self, job: Job) -> Job:
           job.updated_at = datetime.utcnow()
           await self.doc_store.create(self.collection, job.model_dump())
           return job

       async def get(self, entity_id: str) -> Job | None:
           doc = await self.doc_store.read(self.collection, entity_id)
           return Job.model_validate(doc) if doc else None

       async def get_by_task_id(self, task_id: str) -> Job | None:
           docs = await self.doc_store.find(
               self.collection,
               {"celery_task_id": task_id}
           )
           return Job.model_validate(docs[0]) if docs else None

       async def update_status(
           self,
           entity_id: str,
           status: JobStatus,
           result: Any = None,
           error: str | None = None
       ) -> bool:
           update_data = {
               "status": status.value,
               "updated_at": datetime.utcnow().isoformat()
           }
           if result is not None:
               update_data["result"] = result
           if error:
               update_data["error"] = error
           if status == JobStatus.STARTED:
               update_data["started_at"] = datetime.utcnow().isoformat()
           if status in [JobStatus.SUCCESS, JobStatus.FAILURE]:
               update_data["completed_at"] = datetime.utcnow().isoformat()

           return await self.doc_store.update(self.collection, entity_id, update_data)

       async def list(self, filters: dict | None = None) -> list[Job]:
           docs = await self.doc_store.find(self.collection, filters or {})
           return [Job.model_validate(doc) for doc in docs]

       async def delete(self, entity_id: str) -> bool:
           return await self.doc_store.delete(self.collection, entity_id)

       async def get_entity_type(self) -> str:
           return "job"
   ```

3. Register in `src/storage/repositories/registry.py`:
   ```python
   async def initialize(self) -> None:
       if self._initialized:
           return

       self._repositories["tool_response"] = ToolResponseRepository(
           document_store=self.doc_store,
           object_store=self.obj_store,
       )

       self._repositories["job"] = JobRepository(
           document_store=self.doc_store
       )

       # Future: add more repositories here

       self._initialized = True
       set_repository_registry(self)
   ```

**Deliverables**:
- ✅ Job model
- ✅ Job repository
- ✅ Registry updated

---

## Phase 2: Data Access & Exploration (1 week)

### Objectives
- Implement data loading tools
- Implement data exploration tools
- Test end-to-end data workflow

### Tasks

#### Task 2.1: Data Access Tools
**Effort**: 2 days
**Priority**: Critical

**Steps**:
1. Create `src/mcp/tools/data_access/load_csv.py`:
   ```python
   import pandas as pd
   from pathlib import Path
   from src.constants import DATASET_PATH
   from src.mcp.instance import mcp
   from src.mcp.middleware import process_tool
   from src.models.tool_response import ToolResponse

   @mcp.tool
   @process_tool
   async def load_csv(filename: str) -> ToolResponse:
       """Load a CSV file from the datasets folder.

       Args:
           filename: Name of the CSV file (e.g., 'sales.csv')

       Returns:
           ToolResponse with DataFrame in payload and summary statistics

       Example:
           "Load the sales.csv file"
           → load_csv(filename="sales.csv")
       """
       file_path = DATASET_PATH / filename

       if not file_path.exists():
           return ToolResponse(
               payload=None,
               summary=f"Error: File '{filename}' not found in datasets folder",
               metadata={"error": "FileNotFoundError", "filename": filename},
               storage_hint="never"
           )

       # Load CSV
       df = pd.read_csv(file_path)

       # Generate summary
       summary = (
           f"Loaded '{filename}' successfully:\\n"
           f"  - Rows: {len(df):,}\\n"
           f"  - Columns: {len(df.columns)}\\n"
           f"  - Column names: {', '.join(df.columns.tolist()[:10])}"
           f"{'...' if len(df.columns) > 10 else ''}\\n"
           f"  - Memory: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB"
       )

       return ToolResponse(
           payload=df,
           summary=summary,
           metadata={
               "filename": filename,
               "shape": df.shape,
               "columns": df.columns.tolist(),
               "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
               "memory_mb": df.memory_usage(deep=True).sum() / 1024**2
           },
           storage_hint="session",
           suggested_name=filename.replace(".csv", "_data")
       )
   ```

2. Create `src/mcp/tools/data_access/load_dataset.py`:
   ```python
   @mcp.tool
   @process_tool
   async def load_dataset(entity_id: str) -> ToolResponse:
       """Load a previously stored dataset by entity_id.

       Args:
           entity_id: Entity ID of the stored dataset

       Returns:
           ToolResponse with the dataset

       Example:
           "Load the dataset tr_abc123"
           → load_dataset(entity_id="tr_abc123")
       """
       from src.storage.repositories.registry import get_repository_registry

       registry = get_repository_registry()
       entity = await registry.get("tool_response", entity_id)

       if not entity:
           return ToolResponse(
               payload=None,
               summary=f"Error: Dataset with entity_id '{entity_id}' not found",
               metadata={"error": "NotFound", "entity_id": entity_id},
               storage_hint="never"
           )

       df = entity.payload

       summary = (
           f"Loaded dataset '{entity_id}':\\n"
           f"  - Rows: {len(df):,}\\n"
           f"  - Columns: {len(df.columns)}"
       )

       return ToolResponse(
           payload=df,
           summary=summary,
           metadata={"entity_id": entity_id, "shape": df.shape},
           storage_hint="session"
       )
   ```

3. Create tests:
   ```python
   @pytest.mark.integration
   async def test_load_csv():
       """Test loading CSV file."""
       # Create test CSV
       test_df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
       test_file = DATASET_PATH / "test.csv"
       test_df.to_csv(test_file, index=False)

       # Load
       result = await load_csv("test.csv")

       assert "Loaded 'test.csv' successfully" in result.summary
       assert result.payload is not None
       assert len(result.payload) == 3

       # Cleanup
       test_file.unlink()
   ```

**Deliverables**:
- ✅ `load_csv` tool
- ✅ `load_dataset` tool
- ✅ Tests passing

#### Task 2.2: Data Exploration Tools
**Effort**: 3 days
**Priority**: High

**Steps**:
1. Create `src/mcp/tools/exploration/describe_dataset.py`:
   ```python
   @mcp.tool
   @process_tool
   async def describe_dataset(entity_id: str) -> ToolResponse:
       """Get statistical summary of a dataset.

       Args:
           entity_id: Entity ID of the dataset to describe

       Returns:
           ToolResponse with statistics

       Example:
           "Describe the dataset tr_abc123"
           → describe_dataset(entity_id="tr_abc123")
       """
       # Entity resolution handled by middleware
       # df will be available as kwarg after resolution
       pass  # Will be implemented with actual logic
   ```

2. Create `src/mcp/tools/exploration/profile_data.py`:
   ```python
   @mcp.tool
   @process_tool
   async def profile_data(entity_id: str) -> ToolResponse:
       """Comprehensive data profiling including missing values, distributions, etc.

       Args:
           entity_id: Entity ID of the dataset to profile

       Returns:
           ToolResponse with profiling report
       """
       pass  # Implementation
   ```

3. Create `src/mcp/tools/exploration/analyze_correlations.py`:
   ```python
   @mcp.tool
   @process_tool
   async def analyze_correlations(
       entity_id: str,
       target: str | None = None,
       method: str = "pearson"
   ) -> ToolResponse:
       """Analyze correlations in the dataset.

       Args:
           entity_id: Entity ID of the dataset
           target: Optional target column to focus on
           method: Correlation method ('pearson', 'spearman', 'kendall')

       Returns:
           ToolResponse with correlation matrix and insights
       """
       pass  # Implementation
   ```

*(Continue with more exploration tools...)*

**Deliverables**:
- ✅ 5+ exploration tools
- ✅ Tests for each tool
- ✅ Documentation

---

## Phase 3: Feature Engineering & Modeling (1.5 weeks)

*(Similar detailed breakdown for feature engineering and modeling tools)*

---

## Phase 4: Async Jobs & Orchestration (1 week)

### Objectives
- Implement job submission tools
- Implement job monitoring tools
- Wire data science pipelines to async execution

### Tasks

#### Task 4.1: Job Submission Tools
**Effort**: 2 days
**Priority**: Critical

**Steps**:
1. Create `src/mcp/tools/jobs/submit_training_job.py`:
   ```python
   @mcp.tool
   @process_tool
   async def submit_training_job(
       config: dict,
       async_mode: bool = True
   ) -> ToolResponse:
       """Submit a model training job.

       Args:
           config: Training configuration (ExperimentPipelineConfig)
           async_mode: If True, submit to Celery; if False, run synchronously

       Returns:
           ToolResponse with job ID if async, or results if sync

       Example:
           "Train a model with this config"
           → submit_training_job(config={...}, async_mode=True)
       """
       if async_mode:
           # Submit to Celery
           from src.workers.celery_app import app
           from src.models.job import Job, JobStatus
           from src.storage.repositories.registry import get_repository_registry

           task = app.send_task(
               "tasks.train_model",
               args=[config]
           )

           # Create job record
           job = Job(
               celery_task_id=task.id,
               task_name="train_model",
               args=(),
               kwargs={"config": config},
               status=JobStatus.PENDING
           )

           registry = get_repository_registry()
           await registry.save(job)

           summary = (
               f"Training job submitted:\\n"
               f"  - Job ID: {job.entity_id}\\n"
               f"  - Celery Task ID: {task.id}\\n"
               f"  - Status: PENDING\\n\\n"
               f"Use get_job_status(job_id='{job.entity_id}') to check status"
           )

           return ToolResponse(
               payload={"job_id": job.entity_id, "task_id": task.id},
               summary=summary,
               metadata={"job_id": job.entity_id, "async": True},
               storage_hint="always"
           )
       else:
           # Run synchronously
           from src.data_science.pipelines.model_selection import model_selection
           from src.data_science.database.client import DBClient

           db_client = DBClient()
           result = model_selection(config, db_client)

           return ToolResponse(
               payload=result,
               summary="Training completed synchronously",
               metadata={"async": False},
               storage_hint="session"
           )
   ```

2. Implement job monitoring tools
3. Wire all pipelines

*(Continue with detailed steps...)*

---

## Phase 5: Note-Taking & Meta Tools (3 days)

### Objectives
- Implement note-taking system
- Implement meta tools for tool discovery

*(Detailed tasks...)*

---

## Phase 6: Testing & Documentation (1 week)

### Objectives
- Achieve 80%+ test coverage
- Write comprehensive documentation
- Create runbooks

### Tasks

#### Task 6.1: Unit Tests
**Effort**: 2 days
**Target Coverage**: All tools, repositories, middleware

#### Task 6.2: Integration Tests
**Effort**: 2 days
**Target Coverage**: End-to-end workflows

#### Task 6.3: Documentation
**Effort**: 2 days

**Create**:
- API documentation (auto-generated from docstrings)
- Runbooks for common operations
- Troubleshooting guide
- Developer onboarding guide

#### Task 6.4: Tool Examples
**Effort**: 1 day

Create `docs/tool_examples.md` with examples for every tool

---

## Phase 7: Observability & Security (4 days)

### Objectives
- Set up logging, metrics, tracing
- Implement basic security measures

### Tasks

#### Task 7.1: Structured Logging
**Effort**: 1 day

#### Task 7.2: Metrics & Tracing
**Effort**: 1 day

#### Task 7.3: Security
**Effort**: 2 days

- API key authentication
- Input validation
- Audit logging

---

## Testing Strategy

### Unit Tests
- **Target**: 80%+ coverage
- **Focus**: Individual functions, tools, repositories
- **Framework**: pytest
- **Mocking**: Mock external services (Snowflake, MLflow)

### Integration Tests
- **Target**: Critical workflows covered
- **Focus**: Tool chains, end-to-end pipelines
- **Framework**: pytest with Docker services
- **Data**: Use fixtures with sample data

### Performance Tests
- **Target**: Tool response time <2s (p95)
- **Framework**: locust or pytest-benchmark
- **Metrics**: Latency, throughput, resource usage

### Manual QA Checklist
Before each release:
- [ ] All Docker services start cleanly
- [ ] Can load dataset via MCP
- [ ] Can profile dataset
- [ ] Can submit training job
- [ ] Can monitor job completion
- [ ] Can create and retrieve notes
- [ ] Caching works (verify cache hits in logs)
- [ ] Entity resolution works

---

## Deployment Plan

### Development Environment
```bash
# 1. Start services
cd docker && docker compose up -d

# 2. Run migrations (if any)
# (none currently)

# 3. Start MCP server
python -m src.mcp.server

# 4. Start Celery worker
celery -A src.workers.celery_app worker --loglevel=info
```

### Staging/Production
Use Docker Compose with environment-specific `.env` files:

```bash
# Staging
docker compose --env-file .env.staging up -d

# Production
docker compose --env-file .env.production up -d
```

### Rollback Plan
1. Keep previous Docker image tagged
2. Use docker compose down && docker compose up with previous tag
3. Restore MongoDB/MinIO from backup if needed

---

## Success Criteria

### Phase Completion Criteria

**Phase 0: Setup**
- [ ] All Docker services running
- [ ] CI pipeline passing
- [ ] First test passing

**Phase 1: Infrastructure**
- [ ] Entity resolution working
- [ ] Caching functional
- [ ] Celery worker processing tasks
- [ ] Job repository CRUD works

**Phase 2: Data Tools**
- [ ] Can load CSV files
- [ ] Can describe datasets
- [ ] Can profile data
- [ ] Can analyze correlations

**Phase 3: ML Tools**
- [ ] Can create feature pipelines
- [ ] Can train models (sync)
- [ ] Can tune hyperparameters

**Phase 4: Async Jobs**
- [ ] Can submit async training jobs
- [ ] Can monitor job status
- [ ] Can retrieve job results

**Phase 5: Notes**
- [ ] Can create notes
- [ ] Can update notes
- [ ] Can search notes

**Phase 6: Testing**
- [ ] 80%+ test coverage
- [ ] All integration tests passing
- [ ] Documentation complete

**Phase 7: Observability**
- [ ] Structured logging implemented
- [ ] Basic metrics collected
- [ ] Security measures in place

### Overall Success Criteria

**Functional**:
- [ ] Agent can load data
- [ ] Agent can explore data
- [ ] Agent can create features
- [ ] Agent can train models
- [ ] Agent can monitor async jobs
- [ ] Agent can take notes
- [ ] All 50+ tools working

**Non-Functional**:
- [ ] Tool response time <2s (p95)
- [ ] Test coverage >80%
- [ ] CI pipeline green
- [ ] Documentation complete
- [ ] All services healthy in Docker

**Demo Workflow**:
Agent successfully completes this end-to-end task:
1. Load sales.csv
2. Profile the data
3. Identify correlations
4. Create feature pipeline
5. Submit training job (async)
6. Monitor job until complete
7. Retrieve and analyze results
8. Document findings in notes

---

## Risk Mitigation

### Risks & Mitigation Strategies

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Data science pipelines don't work with new architecture | High | Medium | Test early (Phase 3), budget 2 days buffer |
| Entity resolution breaks existing code | Medium | Low | Comprehensive unit tests, backwards compatibility |
| Celery integration issues | High | Medium | Test in Phase 1, allocate debugging time |
| Storage performance issues with large DataFrames | Medium | Medium | Load testing, tune MinIO threshold |
| Test coverage goal not met | Medium | Low | Allocate full week for testing |
| Timeline slips | Medium | Medium | 20% buffer built in, can descope nice-to-haves |

### Contingency Plans

**If timeline slips by >1 week**:
- Descope advanced caching (keep basic deduplication)
- Defer some exploration tools (keep core ones)
- Reduce documentation scope

**If entity resolution too complex**:
- Implement simple version: pass entity_id, tool fetches manually
- Enhance later

**If Celery issues**:
- Start with synchronous execution only
- Add async in Phase 4 as enhancement

---

## Progress Tracking

Use this checklist to track progress:

### Week 1: Foundation
- [ ] Phase 0: Setup (3 days)
- [ ] Phase 1: Infrastructure (4 days)

### Week 2: Data Tools
- [ ] Phase 2: Data Access & Exploration (5 days)

### Week 3: ML Tools
- [ ] Phase 3: Feature Engineering (3 days)
- [ ] Phase 3: Modeling (2 days)

### Week 4: Async & Jobs
- [ ] Phase 4: Async Jobs (5 days)

### Week 5: Notes & Testing
- [ ] Phase 5: Notes (3 days)
- [ ] Phase 6: Testing (2 days)

### Week 6: Polish
- [ ] Phase 6: Documentation (3 days)
- [ ] Phase 7: Observability (2 days)
- [ ] Buffer/final testing (2 days)

---

## Appendix: Tool Inventory

### Data Access (4 tools)
- [x] list_available_datasets (EXISTS)
- [ ] load_csv
- [ ] load_dataset
- [ ] snowflake_query

### Data Exploration (6 tools)
- [ ] describe_dataset
- [ ] profile_data
- [ ] analyze_correlations
- [ ] detect_missing_values
- [ ] visualize_distribution
- [ ] visualize_timeseries

### Feature Engineering (5 tools)
- [ ] create_feature_pipeline
- [ ] apply_transformations
- [ ] list_available_transformations
- [ ] validate_feature_config
- [ ] get_transformation_example

### Modeling (4 tools)
- [ ] submit_training_job
- [ ] submit_hyperparameter_tuning
- [ ] train_model_sync
- [ ] validate_model_config

### Job Management (4 tools)
- [ ] get_job_status
- [ ] get_job_result
- [ ] cancel_job
- [ ] list_jobs

### Model Management (4 tools)
- [ ] register_model
- [ ] list_models
- [ ] compare_models
- [ ] get_model_details

### Deployment (3 tools)
- [ ] create_inference_pipeline
- [ ] batch_predict
- [ ] deploy_model

### Notes (6 tools)
- [ ] create_note
- [ ] update_note
- [ ] append_to_note
- [ ] get_note
- [ ] search_notes
- [ ] list_notes

### Meta (4 tools)
- [x] tool_description (EXISTS)
- [ ] get_tool_examples
- [ ] list_available_tools
- [ ] get_tool_schema

**Total: 40+ tools**

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Create GitHub issues/tasks** for each phase
3. **Set up project board** for tracking
4. **Begin Phase 0** setup work
5. **Schedule daily standups** for progress updates

**Estimated Start Date**: TBD
**Estimated Completion Date**: +6 weeks from start

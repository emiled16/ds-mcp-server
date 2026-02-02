# Bug Tracker

## Active Bugs


---

## Resolved Bugs

### BUG-001: Tools with `entity_id` param receive unexpected `_resolved_entity_id` argument
- **Status**: ✅ Resolved (2026-01-08)
- **Discovered**: 2026-01-07
- **Affected Tools**: `describe_dataset`, `detect_missing_values`, `analyze_correlations`, `profile_data`, `apply_transformation`
- **Error**: `got an unexpected keyword argument '_resolved_entity_id'`
- **Root Cause**: Middleware `resolve_entity_references()` added `_resolved_entity_id` and `_resolved_payload` to kwargs, but these were passed to tool functions that don't accept them
- **Location**: `src/mcp/middleware.py`
- **Fix**: Filter out `_resolved_*` keys before calling tool function

### BUG-002: ScalingNumerical transformation fails with "list index out of range"
- **Status**: ✅ Resolved (2026-01-08)
- **Discovered**: 2026-01-08
- **Error**: `list index out of range`
- **Root Cause**: Complex index handling in `_transform_pandas` broke on default RangeIndex, plus inverted boolean logic
- **Location**: `src/data_science/feature_store/library/transformations/scaling_numerical.py`
- **Fix**: Simplified to directly overwrite columns or add new ones without index manipulation

### BUG-003: submit_training_job was a stub - no actual model training
- **Status**: ✅ Resolved (2026-01-08)
- **Discovered**: 2026-01-08
- **Root Cause**: `train_model` in tasks.py was a placeholder, plus async event loop conflicts
- **Location**: `src/workers/tasks.py`, `src/workers/training.py`, `src/mcp/tools/jobs/submit_training_job.py`
- **Fix**: Implemented `run_training_with_data()` using Snowflake ML models; load DataFrame in async tool before calling sync training

### BUG-004: MLflow DNS rebinding protection blocking requests
- **Status**: ✅ Resolved (2026-01-08)
- **Discovered**: 2026-01-08
- **Error**: `Invalid Host header - possible DNS rebinding attack detected`
- **Root Cause**: MLflow server rejects requests with Host headers not in allowed list; Host header includes port (e.g., `tracking_server:5000`)
- **Location**: `docker/docker-compose.yaml`
- **Fix**: Added `--allowed-hosts "tracking_server:5000,localhost:5000,127.0.0.1:5000"` to MLflow server command

### BUG-005: MLflow run shows "Failed" due to invalid metric name characters
- **Status**: ✅ Resolved (2026-01-08)
- **Discovered**: 2026-01-08
- **Error**: `INVALID_PARAMETER_VALUE: Invalid value "importance_Wind Speed (km/h)" for parameter 'name'`
- **Root Cause**: Feature names with parentheses (e.g., `Wind Speed (km/h)`) create invalid MLflow metric names
- **Location**: `src/workers/training.py`
- **Fix**: Added `sanitize_metric_name()` function to replace invalid characters with underscores

### BUG-006: Minio bucket "mlflow" does not exist
- **Status**: ✅ Resolved (2026-01-08)
- **Discovered**: 2026-01-08
- **Error**: `NoSuchBucket: The specified bucket does not exist`
- **Root Cause**: MLflow artifact storage bucket was never created in Minio
- **Fix**: Created bucket manually: `mc mb local/mlflow`

### BUG-007: MCP server missing REDIS_URL for Celery async jobs
- **Status**: ✅ Resolved (2026-01-08)
- **Discovered**: 2026-01-08
- **Error**: `Retry limit exceeded while trying to reconnect to the Celery redis result store backend`
- **Root Cause**: MCP server container missing `REDIS_URL` env var, defaulting to `localhost:6379`
- **Location**: `docker/docker-compose.yaml`
- **Fix**: Added `REDIS_URL=redis://redis:6379/0` to mcp_server environment

### BUG-008: Celery worker cannot load datasets from MongoDB
- **Status**: ✅ Resolved (2026-01-08)
- **Discovered**: 2026-01-08
- **Error**: `RuntimeError: RepositoryRegistry not initialized. Call initialize() first.`
- **Root Cause**: Celery worker didn't initialize MongoDB/Minio storage on startup
- **Location**: `src/workers/celery_app.py`
- **Fix**: Added `@worker_process_init.connect` signal handler to initialize RepositoryRegistry when worker starts

### BUG-009: Celery worker missing MLFLOW_SERVER_URL
- **Status**: ✅ Resolved (2026-01-08)
- **Discovered**: 2026-01-08
- **Error**: `Failed to establish a new connection: [Errno 111] Connection refused` to localhost:5000
- **Root Cause**: Celery worker container missing `MLFLOW_SERVER_URL` env var
- **Location**: `docker/docker-compose.yaml`
- **Fix**: Added `MLFLOW_SERVER_URL=http://tracking_server:5000` to celery_worker environment

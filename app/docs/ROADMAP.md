# MCP Data Science Agent - Roadmap

## Phase 1: Core Infrastructure Fixes

### 1.1 Fix Job Status Updates
**Priority**: High | **Effort**: Small

Update job status in MongoDB when Celery tasks complete/fail.

**Tasks**:
- [ ] Add async job status update in `CallbackTask.on_success()`
- [ ] Add async job status update in `CallbackTask.on_failure()`
- [ ] Store task result in job record
- [ ] Update `get_job_status` to reflect actual Celery state

**Files**: `src/workers/tasks.py`, `src/models/job.py`

---

## Phase 2: Hyperparameter Tuning

### 2.1 Hyperparameter Tuning Implementation
**Priority**: High | **Effort**: Medium

Implement HPT using existing `data_science` infrastructure.

**Tasks**:
- [ ] Review existing HPT code in `src/data_science/`
- [ ] Create `src/workers/hyperparameter_tuning.py` (similar to `training.py`)
- [ ] Support grid search and random search
- [ ] Log all trials to MLflow as nested runs
- [ ] Return best parameters and metrics
- [ ] Integrate with `tasks.run_hyperparameter_tuning`

**Files**: `src/workers/hyperparameter_tuning.py`, `src/workers/tasks.py`

---

## Phase 3: Model Registry Integration

### 3.1 MLflow Model Registry
**Priority**: High | **Effort**: Small

Register trained models in MLflow Model Registry.

**Tasks**:
- [ ] Add `register_model` parameter to training config
- [ ] Call `mlflow.register_model()` after training
- [ ] Add tool to list registered models
- [ ] Add tool to promote model stages (Staging → Production)
- [ ] Add tool to load model by name/version

**Files**: `src/workers/training.py`, new tools in `src/mcp/tools/models/`

---

## Phase 4: Feature Engineering Pipeline

### 4.1 Feature Pipeline as MLflow PyFunc
**Priority**: High | **Effort**: Large

Create reusable feature pipelines that can be versioned and served.

**Design**:
- Feature pipeline = ordered list of transformations
- Save as `mlflow.pyfunc` model for portability
- Store transformed data for training reuse

**Tasks**:
- [ ] Create `FeaturePipeline` class wrapping multiple transformations
- [ ] Implement `mlflow.pyfunc.PythonModel` interface
- [ ] Add `create_feature_pipeline` tool
- [ ] Add `run_feature_pipeline` tool
- [ ] Save transformed datasets (to Minio/MongoDB)
- [ ] Log pipeline to MLflow as artifact
- [ ] Add `load_feature_pipeline` tool

**Files**: 
- `src/data_science/feature_store/pipeline.py`
- `src/mcp/tools/transformation/feature_pipeline.py`

### 4.2 Transformed Data Storage
**Priority**: Medium | **Effort**: Medium

Save feature pipeline outputs for training reuse.

**Tasks**:
- [ ] Store transformed DataFrames in Minio (parquet format)
- [ ] Track lineage (source dataset → pipeline → transformed dataset)
- [ ] Add `list_transformed_datasets` tool
- [ ] Add `load_transformed_dataset` tool

---

## Phase 5: Complete Pipeline (End-to-End)

### 5.1 Modular Pipeline Orchestration
**Priority**: High | **Effort**: Large

Chain feature engineering → training → HPT in configurable pipelines.

**Design**:
```
Pipeline = {
  "name": "temperature_prediction_v1",
  "steps": [
    {"type": "feature_pipeline", "config": {...}},
    {"type": "training", "config": {...}},
    {"type": "hpt", "config": {...}}  # optional
  ]
}
```

**Tasks**:
- [ ] Create `Pipeline` model/schema
- [ ] Create `PipelineRunner` class
- [ ] Add `create_pipeline` tool
- [ ] Add `run_pipeline` tool (sync/async)
- [ ] Add `list_pipelines` tool
- [ ] Log pipeline runs to MLflow
- [ ] Support pipeline versioning

**Files**:
- `src/models/pipeline.py`
- `src/workers/pipeline_runner.py`
- `src/mcp/tools/pipeline/`

---

## Phase 6: Model Inference

### 6.1 Prediction Tool
**Priority**: Medium | **Effort**: Medium

Make predictions with trained models.

**Tasks**:
- [ ] Add `predict` tool
- [ ] Load model from MLflow by run_id or registered name
- [ ] Apply feature pipeline if specified
- [ ] Return predictions with confidence (if available)
- [ ] Support batch predictions

**Files**: `src/mcp/tools/inference/predict.py`

---

## Phase 7: MLflow Management Tools

### 7.1 Experiment & Run Management
**Priority**: Medium | **Effort**: Small

Tools to query and manipulate MLflow.

**Tasks**:
- [ ] Add `list_experiments` tool
- [ ] Add `list_runs` tool (with filters)
- [ ] Add `compare_runs` tool
- [ ] Add `delete_run` tool
- [ ] Add `set_run_tags` tool

**Files**: `src/mcp/tools/mlflow/`

---

## Phase 8: Evaluation Tools

### 8.1 Pipeline & Model Evaluation
**Priority**: Medium | **Effort**: Medium

Evaluate and compare pipeline outputs.

**Tasks**:
- [ ] Add `evaluate_model` tool (on new data)
- [ ] Add `compare_models` tool
- [ ] Add `evaluate_pipeline` tool
- [ ] Generate evaluation reports
- [ ] Support custom metrics

**Files**: `src/mcp/tools/evaluation/`

---

## Phase 9: Visualization Tools

### 9.1 Data & Model Visualizations
**Priority**: Low | **Effort**: Medium

Generate charts and plots.

**Tasks**:
- [ ] Feature importance bar charts
- [ ] Correlation heatmaps
- [ ] Learning curves
- [ ] Confusion matrices (classification)
- [ ] Residual plots (regression)
- [ ] Save plots to Minio, return URLs

**Files**: `src/mcp/tools/visualization/`

---

## Phase 10: Logging & Observability

### 10.1 Structured Logging
**Priority**: Low | **Effort**: Small

Improve logging across the system.

**Tasks**:
- [ ] Standardize log format (JSON structured)
- [ ] Add correlation IDs for request tracing
- [ ] Log to file + stdout
- [ ] Add log level configuration
- [ ] Integrate with MLflow run logging

**Files**: `src/utils/logging.py`, all modules

---

## Implementation Order

| Phase | Task | Dependencies |
|-------|------|--------------|
| 1.1 | Job Status Updates | None |
| 2.1 | Hyperparameter Tuning | 1.1 |
| 3.1 | Model Registry | 2.1 |
| 4.1 | Feature Pipeline | None |
| 4.2 | Transformed Data Storage | 4.1 |
| 5.1 | Complete Pipeline | 2.1, 4.1 |
| 6.1 | Prediction Tool | 3.1, 4.1 |
| 7.1 | MLflow Management | None |
| 8.1 | Evaluation Tools | 5.1, 6.1 |
| 9.1 | Visualization | 4.1 |
| 10.1 | Logging | None |

---

## Notes

- **Reuse `data_science/`**: All ML implementations should leverage existing code in `src/data_science/`
- **MLflow-first**: Everything should be logged/tracked in MLflow
- **Modularity**: Components should be composable and reusable
- **Async support**: Long-running tasks should support Celery async execution


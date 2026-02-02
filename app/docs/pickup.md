# Pickup Guide for Next Engineer

**Last Updated**: 2026-01-08
**Current Status**: Phase D Complete (Advanced Analytics Platform)

---

## 🎯 Where We Are

### ✅ Completed

1. **Phase 1.1: Job Status Updates** - Celery callbacks update MongoDB job status correctly
2. **Phase 2.1: Hyperparameter Tuning** - Full Optuna-based HPT with MLflow integration
3. **Phase 3.1: MLflow Model Registry** - Register, list, promote, and query models
4. **Phase 4.1: Feature Pipeline as MLflow PyFunc** - Reusable, versioned feature pipelines
5. **Phase 5.1: Complete Pipeline Orchestration** - Chain feature engineering → training → HPT
6. **Phase A: Inference + MLflow Management** ✅
   - **Inference Tools** (4 tools): predict, batch_predict, predict_with_pipeline, load_model_for_inference
   - **MLflow Tools** (5 tools): list_experiments, list_runs, compare_runs, get_run_details, search_runs
7. **Phase B: Model Assessment & Visualization** ✅
   - **Evaluation Tools** (3 tools): evaluate_model, compare_models, cross_validate
   - **Visualization Tools** (4 tools): plot_feature_importance, plot_confusion_matrix, plot_residuals, plot_learning_curves
8. **Phase C: Production Readiness** ✅
   - **Data Validation** (5 tools): validate_schema, validate_types, check_data_quality, detect_outliers, detect_data_drift
   - **Remaining Visualizations** (4 tools): plot_correlation_heatmap, plot_distribution, plot_roc_curve, plot_precision_recall_curve
   - **Data Management** (3 tools): list_transformed_datasets, load_transformed_dataset, get_dataset_lineage
9. **Phase D: Advanced Analytics** ✅
   - **Statistical Analysis** (4 tools): hypothesis_test, ab_test, confidence_interval, significance_test
   - **Model Explainability** (5 tools): explain_with_shap, explain_with_lime, plot_partial_dependence, plot_feature_contributions, explain_prediction

**Total Tools**: 67+ tools across all categories - enterprise-ready ML platform with advanced analytics!

### 🚧 Next Steps (Priority Order)

See `docs/MISSING_FEATURES.md` for complete list. **Recommended Phase E (Model Monitoring & Observability):**

1. **Model Monitoring Tools** (Medium Priority, Large Effort)
   - Track model performance over time
   - Detect prediction drift
   - Model health checks
   - Monitoring dashboards
   - Files: `src/mcp/tools/monitoring/`

**Alternative Phase F (Time Series Analysis):**

1. **Time Series Tools** (Medium Priority, Large Effort)
   - Seasonality detection
   - Time series decomposition
   - Prophet forecasting
   - ARIMA/SARIMA forecasting
   - Time series cross-validation
   - Files: `src/mcp/tools/time_series/`

**Lower Priority Options:**
- AutoML capabilities (Low Priority, Very Large Effort)
- SQL query tools (Low Priority, Small Effort)
- Data sampling & splitting tools (Low Priority, Small Effort)

---

## 📁 Key Files to Know

### Core ML Components

- **`src/workers/training.py`** - Model training logic (Snowflake ML models)

  - `run_training_with_data()` - Main training function
  - `create_model()` - Model factory
  - `evaluate_model()` - Metrics calculation
  - MLflow logging integrated

- **`src/workers/hyperparameter_tuning.py`** - HPT implementation

  - `run_hyperparameter_tuning()` - Main HPT function
  - `run_hpt_trial()` - Single trial execution
  - `create_optuna_suggest_from_space()` - Parameter space conversion
  - Uses Optuna with MLflow nested runs

- **`src/workers/tasks.py`** - Celery task definitions

  - `train_model` - Training task
  - `run_hyperparameter_tuning` - HPT task
  - `CallbackTask` - Base class with status update callbacks

- **`src/workers/celery_app.py`** - Celery configuration
  - Initializes MongoDB registry on worker startup
  - Redis broker/backend configuration

### MCP Tools

- **`src/mcp/tools/jobs/submit_training_job.py`** - Training job submission
- **`src/mcp/tools/jobs/submit_hpt_job.py`** - HPT job submission
- **`src/mcp/tools/jobs/get_job_status.py`** - Job status checking
- **`src/mcp/tools/jobs/get_job_result.py`** - Job result retrieval

### Infrastructure

- **`docker/docker-compose.yaml`** - All services (MCP server, Celery, MLflow, MongoDB, Redis, Minio)
- **`docs/bugs.md`** - Bug tracker (9 bugs fixed, all resolved)

---

## 🏗️ Architecture Overview

### Data Flow

```
MCP Tool → Middleware (entity resolution) → Celery Task → Worker
                                                              ↓
                                                         MongoDB (datasets)
                                                         MLflow (metrics/models)
                                                         Minio (artifacts)
```

### Key Concepts

1. **Entity IDs**: All datasets, jobs, notes have unique entity IDs stored in MongoDB
2. **Middleware**: Resolves entity IDs to actual data before passing to tools
3. **Celery**: Async job execution (training, HPT) runs in separate workers
4. **MLflow**: All metrics, parameters, and models logged to MLflow
5. **Snowflake ML**: Models use Snowflake ML library (works locally with pandas)

---

## 🐛 Known Issues & Gotchas

### Fixed (See `docs/bugs.md`)

- ✅ Job status updates (was broken, now fixed)
- ✅ MLflow DNS rebinding (fixed with `--allowed-hosts`)
- ✅ Metric name sanitization (parentheses → underscores)
- ✅ Minio bucket creation (manual step required)

### Current Limitations

- **No Model Registry**: Models are logged but not registered/versioned
- **No Feature Pipelines**: Transformations are one-off, not reusable
- **No Inference**: Can't make predictions with trained models yet
- **No Pipeline Orchestration**: Can't chain feature → train → HPT

---

## 🧪 Testing

### Manual Testing

1. **Start services**:

   ```bash
   cd docker && docker-compose up -d
   ```

2. **Test training** (sync):

   ```python
   submit_training_job(
       config={
           "dataset_id": "...",
           "model_type": "xgboost",
           "target_column": "Temperature (C)",
           "feature_columns": ["Humidity", "Wind Speed (km/h)"],
           "hyperparameters": {"n_estimators": 50}
       },
       async_mode=False
   )
   ```

3. **Test HPT** (async):

   ```python
   submit_hpt_job(
       config={
           "dataset_id": "...",
           "model_type": "xgboost",
           "target_column": "Temperature (C)",
           "param_space": {
               "n_estimators": {"type": "int", "low": 30, "high": 100},
               "max_depth": {"type": "int", "low": 3, "high": 8}
           },
           "n_trials": 5
       },
       async_mode=True
   )
   ```

4. **Check MLflow**: http://localhost:5000
5. **Check Flower**: http://localhost:5555

### Unit Tests

```bash
pytest tests/unit -v
```

---

## 🔧 Development Workflow

### Making Changes

1. **Edit code** in `src/`
2. **Rebuild Docker**:
   ```bash
   docker-compose build mcp_server celery_worker
   docker-compose up -d mcp_server celery_worker
   ```
3. **Reload MCP connection** in Cursor (or restart Cursor)
4. **Test** via MCP tools

### Adding New Tools

1. Create tool file in `src/mcp/tools/{category}/`
2. Add `@mcp.tool`, `@process_tool`, `@register_tool` decorators
3. Import in `src/mcp/tools/{category}/__init__.py`
4. Import category in `src/mcp/server.py`
5. Rebuild and test

### Adding New Celery Tasks

1. Add task function in `src/workers/tasks.py` with `@app.task(base=CallbackTask)`
2. Create worker function in `src/workers/{module}.py`
3. Create MCP tool to submit task
4. Rebuild `celery_worker` container

---

## 📚 Important Documentation

- **`docs/ROADMAP.md`** - Full implementation roadmap (10 phases)
- **`docs/bugs.md`** - Bug tracker with fixes
- **`docs/ARCHITECTURE.md`** - System architecture details
- **`docs/SYSTEM_PROMPT.md`** - AI agent system prompt

---

## 🚀 Quick Start Checklist

- [ ] Read this document
- [ ] Review `docs/ROADMAP.md` for next steps
- [ ] Check `docs/bugs.md` for known issues
- [ ] Start Docker services: `cd docker && docker-compose up -d`
- [ ] Verify services: MLflow (5000), Flower (5555), MCP (8001)
- [ ] Load a test dataset
- [ ] Run a training job (sync mode)
- [ ] Run an HPT job (async mode)
- [ ] Check MLflow UI for logged runs
- [ ] Check Flower UI for Celery tasks

---

## 💡 Tips

1. **Always rebuild containers** after code changes (Docker caches layers)
2. **Check logs** if something fails: `docker-compose logs {service}`
3. **MLflow experiment**: All runs go to `mcp-ds-agent` (training) or `mcp-ds-agent-hpt` (HPT)
4. **Entity IDs**: Use `load_csv()` to get a dataset entity_id, then pass to training/HPT
5. **Async vs Sync**: Use `async_mode=True` for Celery (visible in Flower), `False` for direct execution

---

## 🎓 Learning Resources

- **Snowflake ML**: Models work locally with pandas DataFrames
- **Optuna**: Used for hyperparameter tuning (see `hyperparameter_tuning.py`)
- **MLflow**: All metrics/models logged here (check UI at localhost:5000)
- **Celery**: Async task queue (check Flower at localhost:5555)

---

## 📞 Questions?

- Check `docs/ARCHITECTURE.md` for system design
- Check `docs/bugs.md` for known issues/fixes
- Review code comments in key files
- Check MLflow/Flower UIs for runtime state

**Good luck! 🚀**

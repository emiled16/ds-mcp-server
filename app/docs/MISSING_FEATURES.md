# Missing Features & Future Development

**Last Updated**: 2026-01-08
**Purpose**: Track missing tools and functionalities for the MAXA Data Scientist Agent

---

## 🔴 High Priority (Critical Gaps)

### 1. Model Inference/Prediction Tools
**Status**: ❌ Not Implemented
**Priority**: Critical
**Effort**: Medium

**Missing Tools:**
- `predict` - Make predictions with trained models
- `batch_predict` - Batch predictions for large datasets
- `predict_with_pipeline` - Apply feature pipeline + predict in one step
- `load_model_for_inference` - Load model from MLflow by name/version/run_id

**Requirements:**
- Load models from MLflow (by run_id, model name, or version)
- Support both single predictions and batch predictions
- Automatically apply feature pipelines if specified
- Return predictions with optional confidence scores
- Handle both sync and async execution

**Files to Create:**
- `src/mcp/tools/inference/__init__.py`
- `src/mcp/tools/inference/predict.py`
- `src/mcp/tools/inference/batch_predict.py`
- `src/mcp/tools/inference/predict_with_pipeline.py`

**Dependencies:**
- Phase 3.1 (Model Registry) ✅
- Phase 4.1 (Feature Pipelines) ✅

---

### 2. Model Evaluation Tools
**Status**: ❌ Not Implemented
**Priority**: Critical
**Effort**: Medium

**Missing Tools:**
- `evaluate_model` - Evaluate model on new data with comprehensive metrics
- `compare_models` - Side-by-side comparison of multiple models
- `cross_validate_model` - K-fold cross-validation
- `generate_evaluation_report` - Comprehensive evaluation with plots

**Requirements:**
- Load model from MLflow
- Compute metrics (accuracy, precision, recall, F1, RMSE, MAE, R2, etc.)
- Support custom metrics
- Generate comparison tables
- Save evaluation results to MLflow
- Support both regression and classification

**Files to Create:**
- `src/mcp/tools/evaluation/__init__.py`
- `src/mcp/tools/evaluation/evaluate_model.py`
- `src/mcp/tools/evaluation/compare_models.py`
- `src/mcp/tools/evaluation/cross_validate.py`

**Dependencies:**
- Inference tools (for predictions)

---

### 3. Data Validation & Quality Tools
**Status**: ❌ Not Implemented
**Priority**: High
**Effort**: Large

**Missing Tools:**
- `validate_schema` - Validate data against expected schema
- `check_data_quality` - Comprehensive data quality checks
- `detect_outliers` - Statistical outlier detection with visualization
- `detect_data_drift` - Compare new data distribution to reference
- `validate_types` - Check column data types

**Requirements:**
- Schema definition and validation (column names, types, ranges)
- Data quality metrics (completeness, uniqueness, validity)
- Statistical outlier detection (IQR, Z-score, Isolation Forest)
- Distribution comparison (KS test, chi-square)
- Detailed reporting of issues found

**Files to Create:**
- `src/mcp/tools/validation/__init__.py`
- `src/mcp/tools/validation/validate_schema.py`
- `src/mcp/tools/validation/check_quality.py`
- `src/mcp/tools/validation/detect_outliers.py`
- `src/mcp/tools/validation/detect_drift.py`
- `src/models/schema.py` (for schema definitions)

**Dependencies:**
- None

---

### 4. MLflow Management Tools
**Status**: ❌ Not Implemented
**Priority**: High
**Effort**: Small

**Missing Tools:**
- `list_experiments` - List all MLflow experiments
- `list_runs` - List runs with filtering (by experiment, metrics, params)
- `compare_runs` - Compare metrics/params across multiple runs
- `get_run_details` - Get detailed info about a specific run
- `delete_run` - Delete runs from MLflow
- `search_runs` - Advanced search with filters

**Requirements:**
- MLflow client integration
- Support filtering and sorting
- Return structured data
- Handle pagination for large result sets
- Metric/param comparison tables

**Files to Create:**
- `src/mcp/tools/mlflow/__init__.py`
- `src/mcp/tools/mlflow/list_experiments.py`
- `src/mcp/tools/mlflow/list_runs.py`
- `src/mcp/tools/mlflow/compare_runs.py`
- `src/mcp/tools/mlflow/get_run_details.py`
- `src/mcp/tools/mlflow/search_runs.py`

**Dependencies:**
- None (MLflow client already available)

---

## 🟡 Medium Priority (Important for Production)

### 5. Visualization Tools
**Status**: ❌ Not Implemented
**Priority**: Medium
**Effort**: Large

**Missing Tools:**
- `plot_feature_importance` - Bar chart of feature importances
- `plot_correlation_heatmap` - Correlation matrix heatmap
- `plot_learning_curves` - Train/val metrics over epochs/iterations
- `plot_confusion_matrix` - Confusion matrix for classification
- `plot_residuals` - Residual plot for regression
- `plot_distribution` - Distribution plots (histogram, KDE, box plot)
- `plot_roc_curve` - ROC curve for binary classification
- `plot_precision_recall_curve` - PR curve for classification

**Requirements:**
- Use matplotlib/seaborn for plotting
- Save plots to MinIO
- Return URLs for plots
- Support both static and interactive plots (plotly)
- Embed plots in tool responses

**Files to Create:**
- `src/mcp/tools/visualization/__init__.py`
- `src/mcp/tools/visualization/plot_feature_importance.py`
- `src/mcp/tools/visualization/plot_correlations.py`
- `src/mcp/tools/visualization/plot_learning_curves.py`
- `src/mcp/tools/visualization/plot_confusion_matrix.py`
- `src/mcp/tools/visualization/plot_residuals.py`
- `src/mcp/tools/visualization/plot_distribution.py`
- `src/utils/plotting.py` (helper functions)

**Dependencies:**
- MinIO for plot storage
- matplotlib, seaborn, plotly

---

### 6. Transformed Data Management
**Status**: ⚠️ Partially Implemented
**Priority**: Medium
**Effort**: Small

**Current State:**
- `create_feature_pipeline` saves transformed data with a generated entity_id
- No easy way to browse or reload transformed datasets

**Missing Tools:**
- `list_transformed_datasets` - Browse transformed datasets with metadata
- `load_transformed_dataset` - Load by name or pipeline
- `get_dataset_lineage` - Show lineage (source → pipeline → transformed)

**Requirements:**
- Metadata tracking (pipeline used, creation date, source dataset)
- Search and filtering
- Lineage visualization
- Version management

**Files to Create:**
- `src/mcp/tools/data_access/list_transformed_datasets.py`
- `src/mcp/tools/data_access/get_dataset_lineage.py`

**Dependencies:**
- Feature pipelines ✅

---

### 7. Model Monitoring & Observability
**Status**: ❌ Not Implemented
**Priority**: Medium
**Effort**: Large

**Missing Tools:**
- `track_model_performance` - Log production model metrics over time
- `detect_prediction_drift` - Monitor prediction distribution changes
- `check_model_health` - Overall model health check
- `create_monitoring_dashboard` - Set up monitoring for a model

**Requirements:**
- Time-series metric storage
- Drift detection algorithms
- Alert thresholds
- Dashboard generation
- Integration with production inference

**Files to Create:**
- `src/mcp/tools/monitoring/__init__.py`
- `src/mcp/tools/monitoring/track_performance.py`
- `src/mcp/tools/monitoring/detect_drift.py`
- `src/models/monitoring.py`

**Dependencies:**
- Inference tools
- Time-series storage

---

### 8. Statistical Analysis Tools
**Status**: ✅ IMPLEMENTED (Phase D - Session 7)
**Priority**: Medium
**Effort**: Medium

**Implemented Tools:**
- ✅ `hypothesis_test` - Comprehensive hypothesis testing (t-test, chi-square, ANOVA, Mann-Whitney, Wilcoxon, Kruskal-Wallis)
- ✅ `ab_test` - A/B test statistical analysis with effect size and confidence intervals
- ✅ `confidence_interval` - Calculate confidence intervals (mean, proportion, median, std, difference)
- ✅ `significance_test` - General significance testing with multiple comparison corrections

**Files Created:**
- ✅ `src/mcp/tools/statistics/__init__.py`
- ✅ `src/mcp/tools/statistics/hypothesis_test.py`
- ✅ `src/mcp/tools/statistics/ab_test.py`
- ✅ `src/mcp/tools/statistics/confidence_interval.py`
- ✅ `src/mcp/tools/statistics/significance_test.py`

---

### 9. Model Explainability Tools
**Status**: ✅ IMPLEMENTED (Phase D - Session 7)
**Priority**: Medium
**Effort**: Large

**Implemented Tools:**
- ✅ `explain_with_shap` - SHAP value explanations with multiple plot types (summary, bar, waterfall, force)
- ✅ `explain_with_lime` - LIME local interpretable explanations
- ✅ `plot_partial_dependence` - Partial dependence plots
- ✅ `plot_feature_contributions` - Feature contribution visualization
- ✅ `explain_prediction` - Comprehensive prediction explanation

**Files Created:**
- ✅ `src/mcp/tools/explainability/__init__.py`
- ✅ `src/mcp/tools/explainability/explain_with_shap.py`
- ✅ `src/mcp/tools/explainability/explain_with_lime.py`
- ✅ `src/mcp/tools/explainability/plot_partial_dependence.py`
- ✅ `src/mcp/tools/explainability/plot_feature_contributions.py`
- ✅ `src/mcp/tools/explainability/explain_prediction.py`

---

### 10. Time Series Specific Tools
**Status**: ❌ Not Implemented
**Priority**: Medium (High if doing time series)
**Effort**: Large

**Missing Tools:**
- `detect_seasonality` - Detect seasonal patterns
- `decompose_time_series` - Trend/seasonal/residual decomposition
- `forecast_prophet` - Facebook Prophet forecasting
- `forecast_arima` - ARIMA/SARIMA forecasting
- `time_series_cv` - Time series cross-validation

**Requirements:**
- Prophet integration
- statsmodels for ARIMA
- ACF/PACF plots
- Seasonal decomposition
- Walk-forward validation

**Files to Create:**
- `src/mcp/tools/time_series/__init__.py`
- `src/mcp/tools/time_series/detect_seasonality.py`
- `src/mcp/tools/time_series/decompose.py`
- `src/mcp/tools/time_series/forecast_prophet.py`
- `src/mcp/tools/time_series/forecast_arima.py`

**Dependencies:**
- prophet, statsmodels packages

---

## 🟢 Lower Priority (Nice to Have)

### 11. AutoML Capabilities
**Status**: ❌ Not Implemented
**Priority**: Low
**Effort**: Very Large

**Missing Tools:**
- `auto_train` - Automatic model selection and training
- `auto_feature_engineering` - Automated feature creation
- `auto_hyperparameter_tune` - More sophisticated HPT
- `neural_architecture_search` - NAS for deep learning

**Requirements:**
- Multiple algorithm trials
- Intelligent search strategies
- Resource management
- Result summarization

**Files to Create:**
- `src/mcp/tools/automl/__init__.py`
- `src/workers/auto_train.py`

**Dependencies:**
- All training infrastructure ✅
- Auto-sklearn or similar

---

### 12. SQL Query Tools
**Status**: ❌ Not Implemented
**Priority**: Low
**Effort**: Small

**Missing Tools:**
- `execute_sql_query` - Run SQL queries on Snowflake
- `save_query_template` - Save reusable query templates
- `list_tables` - List available tables/views
- `describe_table` - Get table schema

**Requirements:**
- Snowflake session management
- Query result caching
- Parameterized queries
- Query validation

**Files to Create:**
- `src/mcp/tools/sql/__init__.py`
- `src/mcp/tools/sql/execute_query.py`
- `src/mcp/tools/sql/list_tables.py`

**Dependencies:**
- Snowflake client ✅

---

### 13. Data Sampling & Splitting Tools
**Status**: ❌ Not Implemented
**Priority**: Low
**Effort**: Small

**Missing Tools:**
- `stratified_sample` - Stratified sampling
- `train_test_split` - Split data for training/testing
- `time_based_split` - Split time series data
- `random_sample` - Random sampling with seed

**Requirements:**
- sklearn.model_selection integration
- Support various splitting strategies
- Reproducibility (random seeds)

**Files to Create:**
- `src/mcp/tools/data_processing/__init__.py`
- `src/mcp/tools/data_processing/sample.py`
- `src/mcp/tools/data_processing/split.py`

**Dependencies:**
- None

---

### 14. Export & Sharing Tools
**Status**: ❌ Not Implemented
**Priority**: Low
**Effort**: Medium

**Missing Tools:**
- `export_dataset` - Export to CSV/Parquet/JSON
- `export_model` - Export in various formats (ONNX, pickle)
- `generate_report` - PDF report generation
- `share_results` - Share via URL

**Requirements:**
- Multiple format support
- Report templates
- URL generation
- MinIO integration for storage

**Files to Create:**
- `src/mcp/tools/export/__init__.py`
- `src/mcp/tools/export/export_dataset.py`
- `src/mcp/tools/export/export_model.py`
- `src/mcp/tools/export/generate_report.py`

**Dependencies:**
- Report generation library (reportlab, weasyprint)

---

### 15. Pipeline Scheduling
**Status**: ❌ Not Implemented
**Priority**: Low
**Effort**: Large

**Missing Tools:**
- `schedule_pipeline` - Schedule pipelines (cron-like)
- `trigger_on_data` - Trigger on data arrival
- `pipeline_dependencies` - Define pipeline DAGs
- `retry_failed_pipeline` - Retry logic

**Requirements:**
- Celery beat integration
- File watchers
- DAG execution engine
- Retry policies

**Files to Create:**
- `src/workers/scheduler.py`
- `src/mcp/tools/scheduling/__init__.py`

**Dependencies:**
- Celery beat
- Pipeline orchestration ✅

---

### 16. Alerts & Notifications
**Status**: ❌ Not Implemented
**Priority**: Low
**Effort**: Small

**Missing Tools:**
- `setup_alert` - Configure alerts on metrics/events
- `send_notification` - Send Slack/email notifications
- `webhook_integration` - Custom webhook triggers

**Requirements:**
- Slack/email integration
- Alert rule engine
- Webhook support

**Files to Create:**
- `src/utils/notifications.py`
- `src/mcp/tools/alerts/__init__.py`

**Dependencies:**
- Slack SDK, email server config

---

### 17. Feature Store Discovery
**Status**: ❌ Not Implemented
**Priority**: Low
**Effort**: Medium

**Missing Tools:**
- `search_features` - Search for features
- `get_feature_metadata` - Feature descriptions
- `feature_lineage` - Track feature creation
- `feature_versions` - Version management

**Requirements:**
- Feature catalog/registry
- Metadata storage
- Search indexing
- Lineage tracking

**Files to Create:**
- `src/models/feature_catalog.py`
- `src/mcp/tools/feature_store/__init__.py`

**Dependencies:**
- Feature pipelines ✅

---

### 18. Advanced Logging
**Status**: ⚠️ Partially Implemented
**Priority**: Low
**Effort**: Small

**Current State:**
- Basic structured logging with loguru
- No correlation IDs or request tracing

**Missing:**
- Correlation IDs for request tracing
- Log aggregation
- Configurable log levels
- Structured logging for all operations
- Log query interface

**Files to Modify:**
- `src/utils/logging.py`
- All tools (add correlation IDs)

**Dependencies:**
- None

---

### 19. Model Deployment Tools
**Status**: ❌ Not Implemented
**Priority**: Low (depends on deployment strategy)
**Effort**: Very Large

**Missing Tools:**
- `deploy_model` - Deploy to serving endpoint
- `create_model_api` - Generate REST API
- `containerize_model` - Create Docker container
- `load_test_model` - Performance testing

**Requirements:**
- Serving infrastructure (FastAPI, TensorFlow Serving, etc.)
- Docker integration
- Load testing tools (locust)
- API generation

**Files to Create:**
- `src/mcp/tools/deployment/__init__.py`
- `src/workers/model_server.py`

**Dependencies:**
- Inference tools
- Docker, FastAPI

---

### 20. Experiment Tracking Enhancements
**Status**: ⚠️ Partially Implemented
**Priority**: Low
**Effort**: Medium

**Current State:**
- Basic MLflow tracking
- No advanced organization or comparison

**Missing:**
- Experiment tagging
- Custom dashboards
- Parameter importance analysis
- Advanced search

**Files to Create:**
- `src/mcp/tools/mlflow/tag_experiment.py`
- `src/mcp/tools/mlflow/analyze_params.py`

**Dependencies:**
- MLflow tools

---

## 📊 Implementation Summary

### By Priority

| Priority | Categories | Estimated Tools | Estimated Effort |
|----------|-----------|-----------------|------------------|
| 🔴 High | 4 | 18 tools | 4-6 weeks |
| 🟡 Medium | 6 | 35 tools | 8-12 weeks |
| 🟢 Low | 10 | 40+ tools | 12-16 weeks |

### By Category

| Category | Priority | Tools | Effort | Dependencies |
|----------|----------|-------|--------|--------------|
| Inference | 🔴 High | 4 | Medium | Model Registry ✅ |
| Evaluation | 🔴 High | 4 | Medium | Inference |
| Data Validation | 🔴 High | 5 | Large | None |
| MLflow Mgmt | 🔴 High | 5 | Small | None |
| Visualization | 🟡 Medium | 8 | Large | MinIO ✅ |
| Data Mgmt | 🟡 Medium | 3 | Small | Pipelines ✅ |
| Monitoring | 🟡 Medium | 4 | Large | Inference |
| Statistics | 🟡 Medium | 4 | Medium | scipy |
| Explainability | 🟡 Medium | 5 | Large | SHAP, LIME |
| Time Series | 🟡 Medium | 5 | Large | Prophet, statsmodels |
| AutoML | 🟢 Low | 4 | Very Large | All training ✅ |
| SQL | 🟢 Low | 4 | Small | Snowflake ✅ |
| Sampling | 🟢 Low | 4 | Small | None |
| Export | 🟢 Low | 4 | Medium | reportlab |
| Scheduling | 🟢 Low | 4 | Large | Celery beat |
| Alerts | 🟢 Low | 3 | Small | Slack SDK |
| Feature Discovery | 🟢 Low | 4 | Medium | Pipelines ✅ |
| Logging | 🟢 Low | 1 | Small | None |
| Deployment | 🟢 Low | 4 | Very Large | Docker |
| Experiment Tracking | 🟢 Low | 2 | Medium | MLflow ✅ |

---

## 🎯 Recommended Implementation Order

### Phase A: Core Prediction Capabilities (Week 1-2)
1. **Inference tools** (4 tools) - Make models usable
2. **MLflow management** (5 tools) - Better visibility

**Impact**: Complete the ML workflow loop

### Phase B: Model Assessment (Week 3-4)
3. **Evaluation tools** (4 tools) - Assess model quality
4. **Visualization basics** (4 tools) - Feature importance, confusion matrix, residuals, learning curves

**Impact**: Scientific model development

### Phase C: Production Readiness (Week 5-8)
5. **Data validation** (5 tools) - Prevent bad data
6. **Remaining visualizations** (4 tools) - Full visual suite
7. **Transformed data management** (3 tools) - Better data organization

**Impact**: Production-grade system

### Phase D: Advanced Analytics (Week 9-12)
8. **Statistical analysis** (4 tools) - Rigorous analysis
9. **Model explainability** (5 tools) - Understand decisions
10. **Time series** (5 tools, if needed) - Domain-specific

**Impact**: Advanced capabilities

### Phase E: Optional Enhancements (As needed)
11. **AutoML** - If time permits
12. **Monitoring** - If deploying to production
13. **Everything else** - Based on user needs

---

## 📝 Notes

- **Current Tool Count**: ~30 tools
- **Missing Tools**: ~93 tools identified
- **Target**: ~120+ total tools for comprehensive platform

**Next Steps:**
1. Review and prioritize this list
2. Create detailed implementation plans for Phase A
3. Begin implementation

**Created**: 2026-01-08
**Author**: Claude (Sonnet 4.5)

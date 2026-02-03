# Regression model registry package.
#
# USE CASE
# --------
# This package supports the lifecycle of trained regression models: list versions,
# promote a version to "production" (or another alias), delete versions, and run
# batch inference. The current implementation is built around Snowflake: models
# are registered and run inside Snowflake; MLflow is used for training and then
# models are pushed into Snowflake's registry and exposed via stored procedures.
#
# The three modules below (snowflake, sproc, utils) are Snowflake-specific. To
# remove them and use only MLflow and/or your own object store, implement the
# replacements described under each module. regression/versioning/tag.py already
# uses MLflow's client for aliases and versioning; you can align the new code
# with that.
#
#
# --- snowflake.py: model catalog and lifecycle in Snowflake ---
# Purpose: Query and mutate the Snowflake model registry (list versions, resolve
# aliases like "PROD", promote a version, delete version or entire model).
#
# To remove: Implement the same operations without Snowflake. You need:
#
#   - set_schema(session, schema_name)
#     Switch active schema/namespace. No-op if you have no schema concept.
#
#   - list_models(session, model_name, database_name, schema_name?) -> DataFrame
#     List all versions of a model with: catalog/schema/name, version name,
#     version_aliases, metrics, comment, owner, created_on, last_altered_on.
#     MLflow: use MlflowClient.get_latest_versions / search_registered_models
#     and run/artifact APIs to build a similar DataFrame.
#
#   - model_version_by_alias(model_name, alias, db, schema) -> version name or None
#     Resolve an alias (e.g. "PROD") to a concrete version name.
#     MLflow: MlflowClient.get_model_version_by_alias(model_name, alias).
#
#   - model_alias_by_version(model_name, version_name, db, schema) -> alias or None
#     Return the alias pointing at this version, if any.
#     MLflow: list aliases for the model and find the one for this version.
#
#   - promote_model_version(model_name, version_name, db, schema, alias="PROD")
#     Make this version the one referenced by alias (e.g. move "PROD" to this version).
#     MLflow: MlflowClient.set_registered_model_alias(model_name, alias, version).
#
#   - delete_model_version(model_name, version_name, db, schema)
#     Delete a single version.
#     MLflow: MlflowClient.delete_model_version(model_name, version_name).
#
#   - drop_model(model_name, db, schema)
#     Delete the entire model (all versions).
#     MLflow: MlflowClient.delete_registered_model(model_name).
#
# See regression/versioning/tag.py for existing MLflow usage (aliases, tags, fetch).
#
#
# --- sproc.py: inference as a Snowflake stored procedure ---
# Purpose: Run batch prediction inside Snowflake by calling a registered stored
# procedure that loads a model from Snowflake's registry and writes predictions
# to a table.
#
# To remove: You need a way to run batch inference without Snowflake stored procs.
#
#   - inference_sp(session, input_table_name, model_name, model_version,
#                  output_table_name, mode)
#     "Run model on input table, write predictions to output table." In a
#     non-Snowflake world: load the model (e.g. from MLflow), read input from
#     your store (DB, GCS, etc.), run predict(), write results. No Snowflake
#     session or table names; use your own I/O (e.g. ObjectStore + MLflow).
#
#   - register_inference_sproc(session, sproc_name, sproc_func, packages, ...)
#     "Register a Python function as a Snowflake stored procedure." Without
#     Snowflake: you don't register a sproc. Instead, expose inference via a
#     job (e.g. Celery task), HTTP endpoint, or serverless function that loads
#     the model and runs inference; "registration" is then deploy/config.
#
#
# --- utils.py: glue between MLflow and Snowflake registry ---
# Purpose: Download models and metadata from MLflow, convert signatures for
# Snowflake, bundle code for Snowpark deployment, and push models into Snowflake's
# registry.
#
# To remove: Keep MLflow-only behavior; drop Snowflake-specific types and calls.
#
#   - process_mlflow_types(data) / process_model_signature(model_conf)
#     Normalize MLflow signature types (e.g. double -> DOUBLE) for Snowflake.
#     If you no longer push to Snowflake, use MLflow signatures as-is or drop.
#
#   - get_model_path_from_mlflow(experiment_name, run_id, artifact_model_name)
#     Download the model artifact for a run to a local path. Keep as-is (MLflow).
#
#   - get_metrics(experiment_name, run_id)
#     Return metrics dict for a run. Keep as-is (MLflow).
#
#   - get_model_data_from_mlflow(experiment_name, run_id, artifact_model_name)
#     Load model, metrics, path, and signature for a run. Keep logic; remove
#     Snowflake ModelSignature if you don't need it.
#
#   - get_model_registry(session, database_name, schema_name)
#     Return a Snowflake Registry instance. Replace with a thin wrapper around
#     MlflowClient (and optional object store) that implements the same
#     high-level operations (log_model, get_model, etc.) using MLflow + GCS/MinIO.
#
#   - bundle_model_files(tmpdir, lib_prefix)
#     Copy project Python files into a directory for Snowpark deployment. Only
#     needed if you deploy to an environment that requires a bundled package;
#     for containers or normal jobs, can be no-op or a different bundling step.
#
#   - register_model_to_snowflake(model_path, model_name, version_name, ...)
#     Upload model and metadata from a local path into Snowflake's registry.
#     Replace with: register_model_to_mlflow(...) using MlflowClient and
#     log_artifact (or track run + register); store artifacts in GCS/MinIO
#     and register the model URI in MLflow.
#
#
# After implementing the above, delete snowflake.py, sproc.py, and utils.py.
# As of now there are no other imports from this package; versioning/tag.py
# uses MlflowClient directly.

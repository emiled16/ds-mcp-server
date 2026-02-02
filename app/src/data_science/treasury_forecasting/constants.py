from pathlib import Path

HOME_PATH = Path.cwd().parent
PREDICTION_COLUMN = "predictions"

DIMENSION_ID_COLUMN = "dim_uid"

STAGE_PATH = "@FORECASTING_EXPERIMENT_DATA.ARTIFACTS"
PIPELINE_PATH_TEMPLATE = f"{STAGE_PATH}/experiment_id={{experiment_id}}/features/feature_store_id={{feature_store_id}}"
RUN_PATH_TEMPLATE = f"{STAGE_PATH}/experiment_id={{experiment_id}}/runs/run_id={{run_id}}"


SEED = 42

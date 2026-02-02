from loguru import logger

from src.data_science.database.client import DBClient, Qualify, table_path_from_orm
from src.data_science.database.models.dim_features import DimFeatures
from src.data_science.database.models.dim_runs import DimRuns
from src.data_science.database.models.hpt_scores import HPTScores
from src.data_science.database.models.model_selection import ModelSelection
from src.data_science.definitions.configs.model_selection import ModelSelectionPipelineConfig
from src.data_science.ds_core.definitions.splitters.enum import Split
from src.data_science.treasury_forecasting.constants import RUN_PATH_TEMPLATE


def model_selection(
    configs: ModelSelectionPipelineConfig,
    db_client: DBClient,
    experiment_id: str | None = None,
    feature_store_id: str | None = None,
) -> None:
    if feature_store_id:
        configs.feature_store_id = feature_store_id
    if experiment_id:
        configs.experiment_id = experiment_id

    if configs.experiment_id is None:
        raise ValueError("Experiment ID is required")

    dim_features = db_client.fetch_records(
        DimFeatures,
        {
            "experiment_id": configs.experiment_id,
            **({"feature_store_id": feature_store_id} if feature_store_id else {}),
        },
        qualify=Qualify(partition_by=["experiment_id"], order_by=["created_at"], asc=False, target=1),
    )

    hpt_scores_table = db_client.fetch_table(
        table_path_from_orm(HPTScores),
        {
            **({"feature_store_id": feature_store_id} if feature_store_id else {}),
            "experiment_id": configs.experiment_id,
            "score_name": configs.objective.metric,
            "split": Split.VALIDATION.value,
        },
    )

    if len(hpt_scores_table) == 0:
        raise ValueError("No scores found in the database")

    best_run_id = hpt_scores_table.sort_values(by="score_value", ascending=configs.direction == "minimize").iloc[0][
        "run_id"
    ]

    dim_runs = db_client.fetch_records(
        DimRuns,
        {
            "experiment_id": configs.experiment_id,
            "run_id": best_run_id,
            **({"feature_store_id": feature_store_id} if feature_store_id else {}),
        },
        qualify=Qualify(partition_by=["experiment_id"], order_by=["created_at"], asc=False, target=1),
    )

    if len(dim_runs) == 0:
        raise ValueError("No runs found in the database")

    best_run_feature_store_id = dim_runs[0]["feature_store_id"]
    best_run_pipeline_path = dim_features[0]["pipeline_path"]

    previous_model = db_client.fetch_records(
        ModelSelection,
        {
            "experiment_id": configs.experiment_id,
            "status": "enabled",
        },
        qualify=Qualify(partition_by=["experiment_id"], order_by=["created_at"], asc=False, target=1),
    )
    if len(previous_model) > 1:
        raise ValueError("Multiple models found in the database")

    if len(previous_model) == 1:
        previous_model = previous_model[0]
        if previous_model["run_id"] == best_run_id:
            logger.info(f"Model {previous_model['model_selection_id']} is already the best model")
            return
        previous_model.update({"status": "disabled"})
        del previous_model["id"]
        del previous_model["created_at"]

        db_client.insert_records(
            ModelSelection,
            [previous_model],
        )

    db_client.insert_records(
        ModelSelection,
        [
            {
                "experiment_id": configs.experiment_id,
                "feature_store_id": best_run_feature_store_id,
                "run_id": best_run_id,
                "pipeline_path": best_run_pipeline_path,
                "model_path": f"{RUN_PATH_TEMPLATE.format(experiment_id=configs.experiment_id, run_id=best_run_id)}/model.zip.gz",
                "status": "enabled",
            },
        ],
    )

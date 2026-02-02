import json
import tempfile
from pathlib import Path

import pandas as pd
from loguru import logger

from src.data_science.database.client import DBClient, Qualify
from src.data_science.database.models import DimExperiments
from src.data_science.database.models.dim_features import DimFeatures
from src.data_science.database.models.feature_store import FeatureStore
from src.data_science.definitions.configs.experiment import ExperimentPipelineConfig
from src.data_science.definitions.configs.feature_store import FeaturePipelineConfig
from src.data_science.utils.nulls import remove_none
from src.data_science.utils.preprocessing import prepare_timeseries


def feature_store(
    configs: FeaturePipelineConfig,
    db_client: DBClient,
    experiment_id: str | None = None,
    feature_store_id: str | None = None,
) -> None:
    if feature_store_id:
        configs.feature_store_id = feature_store_id
    if experiment_id:
        configs.experiment_id = experiment_id

    feature_store_id = configs.feature_store_id
    experiment_id = configs.experiment_id

    logger.info(
        f"Creating feature store for experiment {experiment_id} with feature store id {feature_store_id}",
    )

    if experiment_id is None:
        raise ValueError("Experiment ID must be provided or generated")
    if feature_store_id is None:
        raise ValueError("Feature store ID must be provided or generated")

    # verify that the feature store does not already exist
    existing_feature_store = db_client.fetch_records(
        DimFeatures,
        {"feature_store_id": feature_store_id},
    )
    if len(existing_feature_store) > 0:
        logger.warning(f"Feature store with ID {feature_store_id} already exists. Skipping creation.")
        return feature_store_id

    experiment = db_client.fetch_records(
        DimExperiments,
        {"experiment_id": experiment_id},
        qualify=Qualify(partition_by=["use_case_id"], order_by=["created_at"], asc=False, target=1),
    )
    if len(experiment) == 0:
        raise ValueError(f"Experiment {experiment_id} not found")
    if len(experiment) > 1:
        raise ValueError(f"Multiple experiments found for experiment {experiment_id}")
    experiment = experiment[0]
    logger.info(f"Experiment {experiment_id} found")

    experiment_config = ExperimentPipelineConfig.model_validate(
        remove_none(json.loads(experiment["config"])),
    )
    holdout_splitter = experiment_config.splitters.holdout

    logger.info(f"Loading training data for experiment {experiment_id}")
    raw_data = db_client.fetch_table(experiment_config.data.training_data.to_table().path()).rename(columns=str.lower)
    raw_data = raw_data[
        pd.to_datetime(raw_data[experiment_config.time_series.date_column])
        <= experiment_config.time_series.last_test_date
    ].reset_index(
        drop=True,
    )
    logger.info(f"Preparing timeseries for experiment {experiment_id}")
    timeseries = prepare_timeseries(
        data=raw_data,
        date_column=experiment_config.time_series.date_column,
        dimensions=experiment_config.time_series.dimensions or [],
        metrics_name=experiment_config.time_series.metrics.column,
        aggregation_method=experiment_config.time_series.metrics.aggregation_method,
        aggregated_metrics_name=experiment_config.time_series.metrics.name,
        periodicity=experiment_config.time_series.periodicity,
    )

    train_idx, _ = next(holdout_splitter.split(timeseries))

    timeseries_train = timeseries.loc[train_idx]

    pipeline = configs.feature_store.generate_pipeline()
    logger.info(f"Fitting pipeline for experiment {experiment_id}")
    _ = pipeline.fit_transform(step1__df=timeseries_train)
    feature_table = pipeline.transform(step1__df=timeseries).reset_index()
    columns = feature_table.columns

    logger.info(f"Saving pipeline for experiment {experiment_id}")
    with tempfile.TemporaryDirectory() as temp_dir:
        pipeline.save_pipeline(str(Path(temp_dir) / "pipeline.pkl"))

        target = db_client.upload_files(
            path=Path(temp_dir),
            identifier=f"experiment_id={experiment_id}/features/feature_store_id={feature_store_id}",
        )
        logger.info(f"Pipeline saved to {target}")

    db_client.insert_records(
        DimFeatures,
        [
            {
                "feature_store_id": feature_store_id,
                "experiment_id": experiment_id,
                "name": "feature_store",
                "columns": list(columns),
                "notes": {},
                "config": configs.model_dump(mode="json"),
                "pipeline_path": str(target),
            },
        ],
    )
    logger.info(f"Dim feature created for experiment {experiment_id}")

    feature_table = feature_table.assign(
        feature_store_id=feature_store_id,
        experiment_id=experiment_id,
        data=feature_table[columns].to_dict(orient="records"),
        columns=[list(columns)] * len(feature_table),
    )

    feature_table = feature_table[["feature_store_id", "experiment_id", "columns", "data"]]
    db_client.append_table(FeatureStore, feature_table)

    logger.info(f"Feature store created for experiment {experiment_id} and feature store id {feature_store_id}")

import json
import shutil
import tempfile
import uuid
from pathlib import Path

import mlflow
import pandas as pd
from loguru import logger

from src.data_science.database.client import DBClient, Qualify
from src.data_science.database.models.dim_experiments import DimExperiments
from src.data_science.database.models.dim_runs import DimRuns
from src.data_science.database.models.inference import Inference
from src.data_science.database.models.model_selection import ModelSelection
from src.data_science.definitions.configs.experiment import ExperimentPipelineConfig
from src.data_science.definitions.configs.inference import InferencePipelineConfig
from src.data_science.forecast.predict import predict
from src.data_science.treasury_forecasting.constants import (
    DIMENSION_ID_COLUMN,
    PIPELINE_PATH_TEMPLATE,
    RUN_PATH_TEMPLATE,
)
from src.data_science.utils.extraction import extract_gz_file, extract_zip_file
from src.data_science.utils.nulls import remove_none
from src.data_science.utils.preprocessing import prepare_timeseries


def fetch_model_from_run_id(
    db_client: DBClient,
    run_id: str,
) -> mlflow.pyfunc.PythonModel:
    if run_id is None:
        raise ValueError("Run ID must be provided or generated")
    run = db_client.fetch_records(
        DimRuns,
        {"run_id": run_id},
        # qualify=Qualify(partition_by=["experiment_id"], order_by=["created_at"], asc=False, target=1),
    )
    if len(run) == 0:
        raise ValueError(f"No entries found for run {run_id}")
    if len(run) > 1:
        raise ValueError(f"Multiple runs found for run {run_id}. This should not happen.")

    feature_store_id = run[0].get("feature_store_id")
    experiment_id = run[0].get("experiment_id")

    pipeline_path = (
        PIPELINE_PATH_TEMPLATE.format(experiment_id=experiment_id, feature_store_id=feature_store_id)
        + "/pipeline.pkl.gz"
    )
    model_path = RUN_PATH_TEMPLATE.format(experiment_id=experiment_id, run_id=run_id) + "/model.zip.gz"

    with tempfile.TemporaryDirectory() as temp_dir:
        db_client.download_files(
            path=Path(temp_dir),
            identifier=pipeline_path,
        )
        db_client.download_files(
            path=Path(temp_dir),
            identifier=model_path,
        )

        extract_gz_file(Path(temp_dir) / "pipeline.pkl.gz", Path(temp_dir) / "pipeline.pkl")
        extract_gz_file(Path(temp_dir) / "model.zip.gz", Path(temp_dir) / "model.zip")
        extract_zip_file(Path(temp_dir) / "model.zip", Path(temp_dir) / "model")
        # move the pipeline.pkl to the model directory
        pipeline_dst = Path(temp_dir) / "model" / "model" / "artifacts" / "pipeline.pkl"

        if pipeline_dst.exists():
            pipeline_dst.unlink()
        shutil.move(Path(temp_dir) / "pipeline.pkl", pipeline_dst)

        model = mlflow.pyfunc.load_model(Path(temp_dir) / "model" / "model")
        return model.unwrap_python_model()


def fetch_best_run_id(
    db_client: DBClient,
    experiment_id: str,
) -> str:
    model_selected = db_client.fetch_records(
        ModelSelection,
        {"experiment_id": experiment_id, "status": "enabled"},
        qualify=Qualify(partition_by=["experiment_id"], order_by=["created_at"], asc=False, target=1),
    )
    if len(model_selected) == 0:
        raise ValueError(f"No model found for experiment {experiment_id}")
    if len(model_selected) > 1:
        raise ValueError(f"Multiple models found for experiment {experiment_id}. This should not happen.")
    return model_selected[0]["run_id"]


def fetch_model_from_experiment_id(
    db_client: DBClient,
    experiment_id: str,
) -> mlflow.pyfunc.PythonModel:
    if experiment_id is None:
        raise ValueError("Experiment ID must be provided or generated")

    model_selected = db_client.fetch_records(
        ModelSelection,
        {"experiment_id": experiment_id, "status": "enabled"},
        qualify=Qualify(partition_by=["experiment_id"], order_by=["created_at"], asc=False, target=1),
    )
    if len(model_selected) == 0:
        raise ValueError(f"No model found for experiment {experiment_id}")
    if len(model_selected) > 1:
        raise ValueError(f"Multiple models found for experiment {experiment_id}. This should not happen.")

    pipeline_path = model_selected[0]["pipeline_path"] + "/pipeline.pkl.gz"
    model_path = model_selected[0]["model_path"]

    with tempfile.TemporaryDirectory() as temp_dir:
        db_client.download_files(
            path=Path(temp_dir),
            identifier=pipeline_path,
        )
        db_client.download_files(
            path=Path(temp_dir),
            identifier=model_path,
        )

        extract_gz_file(Path(temp_dir) / "pipeline.pkl.gz", Path(temp_dir) / "pipeline.pkl")
        extract_gz_file(Path(temp_dir) / "model.zip.gz", Path(temp_dir) / "model.zip")
        extract_zip_file(Path(temp_dir) / "model.zip", Path(temp_dir) / "model")
        # move the pipeline.pkl to the model directory
        pipeline_dst = Path(temp_dir) / "model" / "model" / "artifacts" / "pipeline.pkl"

        if pipeline_dst.exists():
            pipeline_dst.unlink()
        shutil.move(Path(temp_dir) / "pipeline.pkl", pipeline_dst)

        model = mlflow.pyfunc.load_model(Path(temp_dir) / "model" / "model")
        return model.unwrap_python_model()


def add_inference_dates(
    timeseries: pd.DataFrame,
    last_date: str,
    index_prefix: str = "_idx",
    date_column: str = "date",
    metric_column: str = "total_amount",
    frequency: str = "D",
) -> pd.DataFrame:
    df = timeseries.copy(deep=True)
    index_names = df.index.names
    date_index_name = f"{date_column}{index_prefix}"
    df = df.reset_index()
    index_names_without_date = [name for name in index_names if name != date_index_name]
    dimensions = [col.split("_idx")[0] for col in index_names_without_date]

    unique_index_values = df[index_names_without_date].drop_duplicates()

    start = pd.to_datetime(df[date_index_name].max()) + pd.Timedelta(1, unit=frequency)
    date_range = pd.date_range(
        start=start,
        end=last_date,
        freq=frequency,
    )

    list_unique_values = list(map(lambda col: unique_index_values[col].unique().tolist(), unique_index_values.columns))
    list_unique_values.append(date_range)

    new_index = []
    for _, i in unique_index_values.iterrows():
        for d in date_range:
            new_index.append([*i, d])
    multi_index = pd.MultiIndex.from_tuples(new_index, names=[*index_names_without_date, date_index_name])

    df = df.set_index(index_names)
    df_before = df.copy(deep=True)
    df = df.reindex(multi_index)

    df[date_column] = df.index.get_level_values(date_index_name)

    df[metric_column] = df[metric_column].fillna(0)
    df = df.reset_index()
    for idx in index_names_without_date:
        df[idx.split("_idx")[0]] = df[idx]
    df = df.set_index(index_names)
    df[DIMENSION_ID_COLUMN] = df[dimensions].apply(
        lambda x: json.dumps(x.to_dict()),
        axis=1,
    )

    return pd.concat([df_before, df])


def inference(
    configs: InferencePipelineConfig,
    db_client: DBClient,
    experiment_id: str | None = None,
    run_id: str | None = None,
    test_date: str | None = None,
) -> None:
    inference_id = str(uuid.uuid4())
    logger.info(f"Starting inference pipeline - inference_id: {inference_id}")

    experiment_id = experiment_id or configs.metadata.experiment_id

    if run_id and not experiment_id:
        experiment_id = db_client.fetch_records(
            DimRuns,
            {"run_id": run_id},
            qualify=Qualify(partition_by=["run_id"], order_by=["created_at"], asc=False, target=1),
        )[0].get("experiment_id")
        configs.metadata.experiment_id = experiment_id
    else:
        run_id = fetch_best_run_id(db_client=db_client, experiment_id=experiment_id)

    if test_date:
        configs.metadata.max_date = test_date

    experiment_id = configs.metadata.experiment_id

    logger.info(f"Fetching experiment {experiment_id} for inference")
    experiment = db_client.fetch_records(
        DimExperiments,
        {"experiment_id": experiment_id},
    )
    if len(experiment) == 0:
        raise ValueError(f"Experiment {experiment_id} not found")

    experiment = experiment[0]

    time_series_config = ExperimentPipelineConfig.model_validate(
        remove_none(json.loads(experiment["config"])),
    ).time_series

    logger.info(f"Fetching input data for inference from {configs.data.inference_input.to_table().path()}")
    input_data = db_client.fetch_table(
        configs.data.inference_input.to_table().path(),
    )

    logger.info("Preparing timeseries data for inference")

    logger.info("Duplicates before")
    logger.info(input_data.duplicated().sum())
    timeseries = prepare_timeseries(
        data=input_data,
        date_column=time_series_config.date_column,
        dimensions=time_series_config.dimensions or [],
        metrics_name=time_series_config.metrics.column,
        aggregation_method=time_series_config.metrics.aggregation_method,
        aggregated_metrics_name=time_series_config.metrics.name,
        periodicity=time_series_config.periodicity,
    )
    logger.info("Duplicates after creating the timeseries")
    logger.info(timeseries.duplicated().sum())

    logger.info("Adding inference dates to timeseries data")
    # Add inference dates to the timeseries data
    timeseries = add_inference_dates(
        timeseries=timeseries,
        last_date=configs.metadata.max_date,
        index_prefix="_idx",
        date_column=time_series_config.date_column,
        metric_column=time_series_config.metrics.name,
        frequency="D",  # TODO: create the mapping so it changes dynamically
    )
    logger.info("Duplicates after adding the inference dates")
    logger.info(timeseries.duplicated().sum())

    # timeseries[timeseries.duplicated()].to_csv("duplicated_timeseries.csv")

    logger.info("Fetching model from experiment ID")
    # model = fetch_model_from_experiment_id(
    #     db_client=db_client,
    #     experiment_id=experiment_id,
    # )
    model = fetch_model_from_run_id(db_client=db_client, run_id=run_id)

    logger.info("Running predictions on the timeseries data")
    predictions = predict(
        model=model,
        data=timeseries,
        first_date_to_predict=configs.metadata.min_date,
        last_date_to_predict=configs.metadata.max_date,
    )

    predictions = timeseries[[*time_series_config.dimensions, time_series_config.date_column]].merge(
        predictions, how="left", on=[*time_series_config.dimensions, time_series_config.date_column]
    )

    predictions = predictions.assign(
        experiment_id=experiment_id,
        features=lambda df: df[model.input_cols].apply(lambda x: x.to_dict(), axis=1),
        prediction_name="predictions",
        prediction_value=lambda df: df["predictions"].fillna(0),
        dimensions=lambda df: df[time_series_config.dimensions].to_dict(orient="records"),
        date=lambda df: df[time_series_config.date_column],
        inference_id=inference_id,
    )

    if configs.metadata.min_date is None:
        predictions = predictions[predictions.date == configs.metadata.max_date]

    else:
        predictions = predictions[
            (predictions.date >= configs.metadata.min_date) & (predictions.date <= configs.metadata.max_date)
        ]

    columns = [
        "inference_id",
        "experiment_id",
        "dimensions",
        "date",
        "features",
        "prediction_name",
        "prediction_value",
    ]

    if predictions.empty:
        logger.info("No predictions to save")
    else:
        logger.info("Saving predictions to the database")
        db_client.append_table(Inference, predictions[columns])

    logger.info("Inference pipeline completed successfully")

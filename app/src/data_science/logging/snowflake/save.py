import json
import tempfile
import zipfile
from pathlib import Path

import mlflow
import pandas as pd
from loguru import logger

from src.data_science.database.client import DBClient
from src.data_science.database.models import HPTForecasts
from src.data_science.database.models.dim_runs import DimRuns
from src.data_science.database.models.hpt_scores import HPTScores
from src.data_science.definitions.configs.hyperparameter_tuning import HyperparameterTuningPipelineConfig
from src.data_science.ds_core.definitions.splitters.enum import Split


def get_artifact_path_from_mlflow(
    experiment_name: str,
    run_id: str,
    tracking_uri: str,
    # artifact_model_name: str = "model",
) -> str:
    client = mlflow.MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        raise ValueError(f"Experiment {experiment_name} not found")
    run = client.get_run(run_id)
    return run.info.artifact_uri.replace("file://", "")


def log_to_snowflake(
    experiment_name: str,
    run_id: str,
    experiment_id: str,
    feature_store_id: str,
    config: HyperparameterTuningPipelineConfig,
    train_predictions: pd.DataFrame,
    train_scores: dict[str, float],
    test_predictions: pd.DataFrame,
    test_scores: dict[str, float],
    features: list[str],
    target_column: str,
    prediction_column: str,
    db_client: DBClient,
    trial_summary: dict,
    tracking_uri: str,
    trial_number: int,
) -> None:
    logger.debug(f"Trial {trial_number} - Log to snowflake - Prepare prediction dataframe")
    predictions = pd.concat(
        [
            pd.DataFrame(train_predictions),
            pd.DataFrame(test_predictions),
        ],
    ).assign(
        run_id=run_id,
        experiment_id=experiment_id,
        feature_store_id=feature_store_id,
        features=lambda df: df[features].apply(lambda x: x.to_dict(), axis=1),
        target_name=target_column,
        target_value=lambda df: df[target_column],
        prediction_name=prediction_column,
        prediction_value=lambda df: df[prediction_column],
        dim_uid=lambda df: df["dim_uid"].apply(json.loads),
    )

    columns = [
        "run_id",
        "experiment_id",
        "feature_store_id",
        "date",
        "dim_uid",
        "features",
        "target_name",
        "target_value",
        "prediction_name",
        "prediction_value",
        "split",
        "fold",
    ]

    logger.debug(f"Trial {trial_number} - Log to snowflake - Insert HPT_FORECASTS - len={len(predictions)}, {run_id=}")
    db_client.append_table(HPTForecasts, predictions[columns])

    logger.debug(f"Trial {trial_number} - Log to snowflake - Prepare scores dataframe")
    # format train scores:
    formatted_scores = [
        {
            "score_name": k.split("__")[0],
            "score_value": v,
            "split": k.split("__")[-1].lower(),
            "run_id": run_id,
            "experiment_id": experiment_id,
            "feature_store_id": feature_store_id,
        }
        for k, v in train_scores.items()
    ]
    for k, v in test_scores.items():
        formatted_scores.append(
            {
                "score_name": k,
                "score_value": v,
                "split": Split.TEST.value,
                "run_id": run_id,
                "experiment_id": experiment_id,
                "feature_store_id": feature_store_id,
            },
        )

    logger.debug(
        f"Trial {trial_number} - Log to snowflake - Insert HPT_SCORES - len={len(formatted_scores)}, {run_id=}"
    )
    db_client.append_table(HPTScores, pd.DataFrame(formatted_scores))

    conf = config.model_dump()
    conf.update({"trial_summary": trial_summary})

    logger.debug(f"Trial {trial_number} - Log to snowflake - Insert DIM_RUNS - len=1, {run_id=}")
    db_client.insert_records(
        DimRuns,
        [
            {
                "run_id": run_id,
                "experiment_id": experiment_id,
                "feature_store_id": feature_store_id,
                "config": conf,
            },
        ],
    )

    model_path = get_artifact_path_from_mlflow(
        experiment_name=experiment_name,
        run_id=run_id,
        tracking_uri=tracking_uri,
    ).replace("/C:", "")

    # List all files recursively and log them for debugging
    all_paths = list(Path(model_path).rglob("*"))
    files = [file for file in all_paths if file.is_file()]

    logger.debug(f"Trial {trial_number} - Log to snowflake - Create zip with {len(files)} files in {model_path=}")
    with tempfile.TemporaryDirectory() as tmp_dir:
        with zipfile.ZipFile(Path(tmp_dir) / "model.zip", "w") as zipf:
            for file in files:
                zipf.write(file, file.relative_to(model_path).as_posix())

        logger.debug(f"Trial {trial_number} - Log to snowflake - Upload files for {run_id=} and {experiment_id=}")
        db_client.upload_files(
            path=Path(tmp_dir),
            identifier=f"experiment_id={experiment_id}/runs/run_id={run_id}",
        )

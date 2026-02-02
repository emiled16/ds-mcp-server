import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Union

import mlflow
import pandas as pd
from loguru import logger
from mlflow.models.signature import ModelSignature
from snowflake import snowpark

from src.data_science.ds_core.definitions.splitters import Splitter
from src.data_science.regression.configs.run import RunConfig
from src.data_science.regression.metrics import Scorer
from src.data_science.regression.models.custom import CustomModel
from src.data_science.regression.run.local import summarize_scores
from src.data_science.regression.utils.mlflow import is_mlflow_server_running


def log_run(func: Callable) -> Callable:
    def wrapper(
        dataset: Union[pd.DataFrame, snowpark.DataFrame],
        python_model: CustomModel,
        splitter: Splitter,
        scorer: Scorer,
        target_cols: list[str],
        output_cols: list[str],
        input_cols: list[str],
        config: RunConfig,
        trial_number: int,
        is_running_in_sproc: bool = False,
        save_dataset: bool = False,
    ) -> tuple[Any, ModelSignature, dict[str, float], pd.DataFrame, str]:
        logger.debug(f"Trial {trial_number} - Run - Setup")
        if isinstance(dataset, snowpark.DataFrame):
            dataset = dataset.to_pandas()

        tracking_uri = config.tracking_uri

        if is_running_in_sproc:
            # if running inside a stored procedure, we need to set the tracking uri to /tmp/mlruns (no other option)
            tracking_uri = "/tmp/mlruns"
            if not is_mlflow_server_running(tracking_uri):
                logger.warning("MLflow server is not running, using default tracking uri")
        if tracking_uri is None:
            tracking_uri = mlflow.get_tracking_uri()

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name=config.experiment_name)

        logger.debug(f"Trial {trial_number} - Run - Start Run")
        with mlflow.start_run():
            if config.tags:
                mlflow.set_tags(config.tags)

            logger.debug(f"Trial {trial_number} - Run - Log saved dataset")
            if dataset is not None and save_dataset:
                # save the dataset as an artifact
                file_name = "dataset.csv" if not is_running_in_sproc else "/tmp/dataset.csv"
                dataset.to_csv(file_name)
                mlflow.log_artifact(file_name)
                os.remove(file_name)

                # save the dataset as a dataset input
                saved_dataset = mlflow.data.from_pandas(
                    dataset,
                    name="training_dataset",
                    targets=target_cols[0],  # assuming only one target column
                    source=f"{mlflow.active_run().info.artifact_uri}/dataset.csv",
                )
                mlflow.log_input(saved_dataset, context="training")

            logger.debug(f"Trial {trial_number} - Run - Log config")
            mlflow.log_params(config.model_dump(exclude={"model": {"model_class"}}))

            logger.debug(f"Trial {trial_number} - Run - Execute Launch")
            python_model, model_signature, scores, predictions = func(
                dataset=dataset,
                python_model=python_model,
                splitter=splitter,
                scorer=scorer,
                target_cols=target_cols,
                output_cols=output_cols,
                input_cols=input_cols,
                logger_context=f"Trial {trial_number} - Run - Launch",
            )
            logger.debug(f"Trial {trial_number} - Run - Summarize scores")

            mlflow.log_metrics(summarize_scores(scores))
            # mlflow.log_metrics(flatten_scores(scores))
            run = mlflow.active_run()
            if run is None:
                raise ValueError("No active run found")
            run_id = run.info.run_id

            ###############################################################################################
            # file_name = f"predictions_{run_id}.csv" if not is_running_in_sproc else "/tmp/predictions.csv"
            # predictions.to_csv(file_name)
            # mlflow.log_artifact(file_name)
            # os.remove(file_name)

            logger.debug(f"Trial {trial_number} - Run - Save artifacts")
            with tempfile.TemporaryDirectory() as tmp_dir:
                model_path = Path(tmp_dir) / "model"
                python_model.save_artifacts(model_path)

                mlflow.pyfunc.log_model(
                    python_model=python_model,
                    artifact_path="model",  # TODO: model name should not be in deployment config
                    signature=model_signature,
                    artifacts={
                        "pipeline": str(model_path / "pipeline.pkl"),
                        "model": str(model_path / "model.pkl"),
                    },
                )

        return (python_model, model_signature, summarize_scores(scores), predictions, run_id, scores)

    return wrapper

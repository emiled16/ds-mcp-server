from typing import Callable

import numpy as np
import optuna
import pandas as pd
from loguru import logger

from src.data_science.database.client import DBClient
from src.data_science.definitions.configs.components.experiments import ExperimentsConfig
from src.data_science.definitions.configs.hyperparameter_tuning import HyperparameterTuningPipelineConfig
from src.data_science.ds_core.definitions.orchestration.pipeline import Pipeline
from src.data_science.ds_core.definitions.splitters import Splitter
from src.data_science.ds_core.definitions.splitters.enum import Split
from src.data_science.forecast.model import TimeSeriesForecastingModelWithFeatureSelection
from src.data_science.logging.snowflake.save import log_to_snowflake
from src.data_science.regression.metrics import Scorer
from src.data_science.regression.models import RegressorGridSearchConfig
from src.data_science.regression.run.run import launch_run
from src.data_science.utils.gridsearch import suggest_features, suggest_model
from src.data_science.utils.postprocessing import postprocess_predictions


def create_objective(
    train_data: pd.DataFrame,
    test_data: pd.DataFrame,
    models: list[RegressorGridSearchConfig],
    backtest_splitter: Splitter,
    scorer: Scorer,
    metric_to_optimize: str,
    date_column: str,
    dimensions: list[str],
    mandatory_features: list[str],
    optional_features: list[str],
    metrics_name: str,
    target_column: str,
    prediction_column: str,
    db_client: DBClient,
    experiment_id: str,
    feature_store_id: str,
    experiment_config: ExperimentsConfig,
    hyperparameter_tuning_config: HyperparameterTuningPipelineConfig,
    pipeline: Pipeline | None = None,
    take_last_x_months: int | None = None,
) -> Callable:
    def objective(trial: optuna.Trial) -> np.float64:
        logger.debug(f"Trial {trial.number} - Suggest features")
        forecasting_input_cols = suggest_features(trial, mandatory_features, optional_features)
        forecasting_target_cols = [target_column]
        forecasting_output_cols = [prediction_column]

        logger.debug(f"Trial {trial.number} - Suggest model")
        forecasting_model = suggest_model(
            trial,
            models,
            forecasting_input_cols,
            forecasting_target_cols,
            forecasting_output_cols,
        )
        model = TimeSeriesForecastingModelWithFeatureSelection(
            pipeline=pipeline,
            model=forecasting_model,
            selected_features=forecasting_input_cols,
            date_column=date_column,
            dimensions=dimensions,
            metrics_name=metrics_name,
        )

        logger.debug(f"Trial {trial.number} - Launch run")
        python_model, model_signature, scores, predictions, run_id, raw_scores = launch_run(
            dataset=train_data,
            python_model=model,
            splitter=backtest_splitter,
            scorer=scorer,
            target_cols=forecasting_target_cols,
            output_cols=forecasting_output_cols,
            input_cols=forecasting_input_cols,
            config=experiment_config,
            trial_number=trial.number,
            on_snowflake=experiment_config.tracking_uri == "file:///tmp/mlruns",
        )

        logger.debug(f"Trial {trial.number} - Postprocess predictions")
        test_predictions, test_scores, fig = postprocess_predictions(
            model=python_model,
            train_data=train_data,
            test_data=test_data,
            predictions=predictions,
            date_column=date_column,
            forecasting_target_cols=forecasting_target_cols,
            forecasting_output_cols=forecasting_output_cols,
            prediction_column=prediction_column,
            scorer=scorer,
        )

        trial_summary = {trial.number: trial.params}

        logger.info(f"Trained model with run_id: {run_id} and trial_number: {trial.number}")

        logger.debug(f"Trial {trial.number} - Log to snowflake")
        log_to_snowflake(
            experiment_name=experiment_config.experiment_name,
            run_id=run_id,
            experiment_id=experiment_id,
            feature_store_id=feature_store_id,
            config=hyperparameter_tuning_config,
            train_predictions=predictions,
            train_scores=scores,
            test_predictions=test_predictions,
            test_scores=test_scores,
            features=forecasting_input_cols,
            target_column=target_column,
            prediction_column=prediction_column,
            db_client=db_client,
            trial_summary=trial_summary,
            tracking_uri=experiment_config.tracking_uri,
            trial_number=trial.number,
        )

        # compute geometric mean for validation absolute net error

        net_errors = [v[Split.VALIDATION.value][metric_to_optimize] for k, v in raw_scores.items()]
        gamma = 0.9
        # discounted_errors = [error * (gamma**i) for i, error in enumerate(net_errors[::-1])][::-1]
        # last_x_discounted_error = discounted_errors[-take_last_x_months:] if take_last_x_months else discounted_errors
        # mean_discounted_error = np.mean(last_x_discounted_error)
        last_x_errors = net_errors[-take_last_x_months:] if take_last_x_months else net_errors
        mean_net_abs_errors = np.mean(last_x_errors)
        std_net_abs_errors = np.std(last_x_errors)

        logger.debug(f"Trial {trial.number} - Return {mean_net_abs_errors=:.3f}")
        return mean_net_abs_errors
        # return np.sqrt(mean_net_abs_errors * std_net_abs_errors)

    return objective

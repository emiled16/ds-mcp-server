import json

import optuna
import pandas as pd
from loguru import logger
from optuna.pruners import NopPruner
from optuna.samplers import TPESampler

from src.data_science.database.client import DBClient, Qualify
from src.data_science.database.models import DimExperiments, DimFeatures, FeatureStore
from src.data_science.definitions.configs.experiment import ExperimentPipelineConfig
from src.data_science.definitions.configs.hyperparameter_tuning import HyperparameterTuningPipelineConfig
from src.data_science.forecast.objective import create_objective
from src.data_science.regression.metrics import Scorer
from src.data_science.treasury_forecasting.constants import PREDICTION_COLUMN
from src.data_science.utils.nulls import remove_none


def hyperparameter_tuning(
    configs: HyperparameterTuningPipelineConfig,
    db_client: DBClient,
    feature_store_id: str | None = None,
) -> None:
    if feature_store_id:
        configs.runs.feature_store_id = feature_store_id

    feature_store_id = configs.runs.feature_store_id
    feature_dimension = db_client.fetch_records(
        DimFeatures,
        {"feature_store_id": feature_store_id},
        qualify=Qualify(partition_by=["experiment_id"], order_by=["created_at"], asc=False, target=1),
    )

    if len(feature_dimension) == 0:
        raise ValueError(f"Feature store {feature_store_id} not found")
    if len(feature_dimension) > 1:
        raise ValueError(f"Multiple feature dimensions found for feature store {feature_store_id}")

    feature_dimension = feature_dimension[0]
    logger.info(f"Feature store id  {feature_store_id} found")

    experiment_id = feature_dimension["experiment_id"]

    experiment_dimension = db_client.fetch_records(
        DimExperiments,
        {"experiment_id": experiment_id},
        qualify=Qualify(partition_by=["use_case_id"], order_by=["created_at"], asc=False, target=1),
    )
    if len(experiment_dimension) == 0:
        raise ValueError(f"Experiment {experiment_id} not found")
    if len(experiment_dimension) > 1:
        raise ValueError(f"Multiple experiments found for experiment {experiment_id}")
    experiment_dimension = experiment_dimension[0]
    logger.info(f"Experiment {experiment_id} found")

    experiment_config = ExperimentPipelineConfig.model_validate(
        remove_none(json.loads(experiment_dimension["config"])),
    )

    logger.info(f"Loading feature store table - {feature_store_id}")
    feature_store_table = db_client.fetch_table(
        f"{FeatureStore.__table__.schema}.{FeatureStore.__table__.name}",
        filters={
            "feature_store_id": feature_store_id,
        },
    )

    feature_store = pd.json_normalize(
        feature_store_table.assign(
            data=lambda _d: _d["data"].apply(json.loads),
        )["data"],
    )

    if configs.schema.index is not None:
        feature_store = feature_store.set_index(configs.schema.index)

    holdout_splitter = experiment_config.splitters.holdout
    backtest_splitter = experiment_config.splitters.backtest

    scorer = Scorer(
        metrics=[*configs.scoring_metrics.to_log, configs.scoring_metrics.to_optimize.objective]
        if configs.scoring_metrics.to_optimize.objective.metric
        not in [m.metric for m in configs.scoring_metrics.to_log]
        else configs.scoring_metrics.to_log,
    )

    train_idx, test_idx = next(holdout_splitter.split(feature_store))
    train_data, test_data = feature_store.loc[train_idx], feature_store.loc[test_idx]

    logger.info(f"Train Data - len={len(train_data)}, size={memory_size_mo(train_data):.3f} Mo")
    logger.info(f"Test Data - len={len(test_data)}, size={memory_size_mo(test_data):.3f} Mo")

    objective = create_objective(
        train_data=train_data,
        test_data=test_data,
        models=configs.models,
        pipeline=None,
        backtest_splitter=backtest_splitter,
        scorer=scorer,
        date_column=configs.schema.date,
        dimensions=configs.schema.dimensions or [],
        mandatory_features=configs.schema.features.mandatory,
        optional_features=configs.schema.features.optional,
        metrics_name=configs.schema.target,
        target_column=configs.schema.target,
        metric_to_optimize=configs.scoring_metrics.to_optimize.objective.metric,
        prediction_column=PREDICTION_COLUMN,
        experiment_id=experiment_id,
        feature_store_id=feature_store_id,
        # TODO: would be cool to pass using globals
        experiment_config=experiment_config.experiments,
        hyperparameter_tuning_config=configs,
        db_client=db_client,
        take_last_x_months=configs.scoring_metrics.take_last_x_months,
    )

    sampler = TPESampler(
        n_startup_trials=max(50, configs.runs.runs_number // 5),  # 20% random exploration
        n_ei_candidates=50,  # More candidates for better exploration
        multivariate=True,  # Capture parameter dependencies
        group=True,  # Group related parameters
        constant_liar=True,  # Better parallel optimization if needed
        seed=24,
    )

    pruner = NopPruner()

    study = optuna.create_study(
        direction=configs.scoring_metrics.to_optimize.direction,
        study_name=experiment_config.experiments.experiment_name,
        pruner=pruner,
        sampler=sampler,
        # storage=experiment_config.experiments.backend_storage_uri
        # if experiment_config.experiments.backend_storage_uri
        # else f"sqlite:///{experiment_config.experiments.experiment_name}.db",
        # load_if_exists=True,
    )

    logger.info(f"Start study optimization - n_trials={configs.runs.runs_number}")
    study.optimize(objective, n_trials=configs.runs.runs_number, n_jobs=-1)

    logger.info(f"The best trial is {study.best_trial}")
    logger.info(f"The best trial params are {study.best_trial.params}")
    logger.info(f"The best trial value is {study.best_trial.value}")


def memory_size_mo(data: pd.DataFrame) -> int:
    mo_size = 1024 * 1024
    return data.memory_usage(deep=True).sum() / mo_size

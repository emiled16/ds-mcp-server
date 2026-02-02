from functools import partial
from typing import Callable, Literal, Optional, Union

import optuna
import pandas as pd
from optuna import Study, Trial
from pydantic import BaseModel, Field
from snowflake import snowpark

from src.data_science.ds_core.definitions.orchestration.pipeline import Pipeline
from src.data_science.ds_core.definitions.splitters import Splitter
from src.data_science.feature_store.src.config import Config as FeatureStoreConfig
from src.data_science.regression.configs.run import RunConfig
from src.data_science.regression.metrics import Metric, Scorer
from src.data_science.regression.models import RegressorGridSearchConfig
from src.data_science.regression.models.custom import CustomModel
from src.data_science.regression.run.run import launch_run


class ExperimentConfig(BaseModel):
    experiment_name: Optional[str] = None
    tracking_uri: Optional[str] = None
    tags: Optional[dict] = None
    input_cols: list[str]
    output_cols: list[str]
    target_cols: list[str]
    pipeline: FeatureStoreConfig = Field(default_factory=FeatureStoreConfig)
    grid_search_config: RegressorGridSearchConfig
    splitter: Splitter
    metrics: list[Metric]  # metrics to track
    metric_to_optimize: Metric
    direction: Literal["maximize", "minimize"]
    engine: Optional[Literal["local", "snowflake"]] = "local"

    def get_scorer(self) -> Scorer:
        return Scorer(metrics=self.metrics)

    def get_pipeline(self) -> Pipeline:
        return self.pipeline.generate_pipeline()

    def get_splitter(self) -> Splitter:
        return self.splitter

    def get_metrics(self) -> list[Metric]:
        return self.metrics

    def get_model_grid(self) -> RegressorGridSearchConfig:
        return self.grid_search_config


def objective(
    trial: Trial,
    dataset: Union[pd.DataFrame, snowpark.DataFrame],
    metric_to_optimize: Metric,
    pipeline: Pipeline,
    splitter: Splitter,
    scorer: Scorer,
    model_grid: RegressorGridSearchConfig,
    target_cols: list[str],
    output_cols: list[str],
    input_cols: list[str],
    exp_config: ExperimentConfig,
    on_snowflake: bool = False,
) -> float:
    model_config = model_grid.get_optuna_grid_search_callable()(trial)

    run_config = RunConfig.model_validate(
        {
            "experiment_name": exp_config.experiment_name,
            "tracking_uri": exp_config.tracking_uri,
            "tags": exp_config.tags,
            "model": model_config,
            "input_cols": input_cols,
            "output_cols": output_cols,
            "target_cols": target_cols,
            "splitter": exp_config.splitter,
            "metrics": exp_config.metrics,
        },
    )
    # 1. just used for the pydantic discriminator to get the model, could be rethinked in the future
    # 2. the logger needs a run_config to log some metadata, # TODO: absract away a metadata config, that will only be used for logging
    python_model = CustomModel(pipeline=pipeline, model=run_config.get_model())
    trained_model, model_signature, scores, predictions, run_id = launch_run(
        config=run_config,
        dataset=dataset,
        on_snowflake=on_snowflake,
        python_model=python_model,
        splitter=splitter,
        scorer=scorer,
        target_cols=target_cols,
        output_cols=output_cols,
        input_cols=input_cols,
        trial_number=trial.number,
    )

    return scores[f"{metric_to_optimize.metric}__validation"]


def get_study_from_exp_config(
    exp_config: ExperimentConfig,
    dataset: Union[pd.DataFrame, snowpark.DataFrame],
    on_snowflake: bool = False,
) -> tuple[Study, Callable]:
    target_cols = exp_config.target_cols
    output_cols = exp_config.output_cols
    input_cols = exp_config.input_cols

    model_grid = exp_config.get_model_grid()
    pipeline = exp_config.get_pipeline()
    splitter = exp_config.get_splitter()
    scorer = exp_config.get_scorer()

    study = optuna.create_study(
        study_name=exp_config.experiment_name,
        direction=exp_config.direction,
    )

    objective_func = partial(
        objective,
        dataset=dataset,
        on_snowflake=on_snowflake,
        metric_to_optimize=exp_config.metric_to_optimize,
        pipeline=pipeline,
        splitter=splitter,
        scorer=scorer,
        model_grid=model_grid,
        target_cols=target_cols,
        output_cols=output_cols,
        input_cols=input_cols,
        exp_config=exp_config,
    )
    return study, objective_func


def get_study_raw(
    model_grid: RegressorGridSearchConfig,
    pipeline: Pipeline,
    splitter: Splitter,
    scorer: Scorer,
    target_cols: list[str],
    output_cols: list[str],
    input_cols: list[str],
    exp_config: ExperimentConfig,
    metric_to_optimize: Metric,
    direction: Literal["maximize", "minimize"],
    study_name: str,
    dataset: Union[pd.DataFrame, snowpark.DataFrame],
    on_snowflake: bool = False,
) -> tuple[Study, Callable]:
    study = optuna.create_study(
        study_name=study_name,
        direction=direction,
    )

    objective_func = partial(
        objective,
        dataset=dataset,
        on_snowflake=on_snowflake,
        metric_to_optimize=metric_to_optimize,
        pipeline=pipeline,
        splitter=splitter,
        scorer=scorer,
        model_grid=model_grid,
        target_cols=target_cols,
        output_cols=output_cols,
        input_cols=input_cols,
        exp_config=exp_config,
    )
    return study, objective_func

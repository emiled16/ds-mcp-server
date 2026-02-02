from typing import Any

from optuna import Trial
from pydantic import BaseModel

from src.data_science.regression.models import RegressorGridSearchConfig, RegressorModel
from src.data_science.regression.models.base import SnowflakeModelClassType


def get_model_from_model_config(
    model_config: dict[str, Any],
    input_cols: list[str] | str | None = None,
    output_cols: list[str] | str | None = None,
    target_cols: list[str] | str | None = None,
    passthrough_cols: list[str] | str | None = None,
) -> SnowflakeModelClassType:
    class Forecaster(BaseModel):
        model: RegressorModel

    return Forecaster.model_validate({"model": model_config}).model.get_model(
        input_cols=input_cols,
        output_cols=output_cols,
        target_cols=target_cols,
        passthrough_cols=passthrough_cols,
    )


def suggest_model(
    trial: Trial,
    models: list[RegressorGridSearchConfig],
    input_cols: list[str],
    target_cols: list[str],
    output_cols: list[str],
) -> SnowflakeModelClassType:
    return get_model_from_model_config(
        next(
            model
            for model in models
            if model.model == trial.suggest_categorical("model", [model.model for model in models])
        ).get_optuna_grid_search_callable()(trial),
        input_cols=input_cols,
        target_cols=target_cols,
        output_cols=output_cols,
    )


def suggest_features(trial: Trial, mandatory_features: list[str], optional_features: list[str]) -> list[str]:
    return [
        feature
        for feature, selected in {
            feature: trial.suggest_categorical(feature, [True, False]) for feature in optional_features
        }.items()
        if selected
    ] + mandatory_features

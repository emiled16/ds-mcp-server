"""Base regression model using sklearn-compatible API."""

from collections.abc import Callable, Iterable
from typing import Any, Literal

import pandas as pd
from optuna import Trial
from pydantic import BaseModel, ConfigDict
from sklearn.base import RegressorMixin

# Type for sklearn-compatible regressors (used by gridsearch, configs)
SklearnModelClassType = RegressorMixin

__all__ = [
    "BaseRegressionModel",
    "BaseRegressionModelGridSearchConfig",
    "SklearnModelClassType",
    "SklearnRegressorWrapper",
]


class SklearnRegressorWrapper:
    """Wraps sklearn regressor to match Snowflake ML API: fit(df), predict(df) -> df with output_col."""

    def __init__(
        self,
        model: RegressorMixin,
        input_cols: list[str],
        output_cols: list[str],
        label_cols: list[str],
    ):
        self.model = model
        self.input_cols = input_cols
        self.output_cols = output_cols
        self.label_cols = label_cols

    def fit(self, df: pd.DataFrame) -> "SklearnRegressorWrapper":
        X = df[self.input_cols].fillna(0)
        y = df[self.label_cols[0]]
        self.model.fit(X, y)
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        X = df[self.input_cols].fillna(0)
        preds = self.model.predict(X)
        result = df.copy()
        result[self.output_cols[0]] = preds
        return result

    @property
    def _sklearn_object(self) -> RegressorMixin:
        return self.model


class BaseRegressionModel(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        protected_namespaces=(),
    )
    model: Literal[
        "GradientBoostingRegressor",
        "RandomForestRegressor",
        "LinearRegressionRegressor",
        "LassoRegressor",
        "ElasticNetRegressor",
        "HuberRegressor",
        "DecisionTreeRegressor",
        "NeuralNetworkRegressor",
    ]
    model_class: type[RegressorMixin]

    def get_model(
        self,
        input_cols: str | Iterable[str] | None = None,
        output_cols: str | Iterable[str] | None = None,
        target_cols: str | Iterable[str] | None = None,
        passthrough_cols: str | Iterable[str] | None = None,
    ) -> SklearnRegressorWrapper:
        input_cols = list(input_cols) if input_cols else []
        output_cols = list(output_cols) if output_cols else []
        label_cols = list(target_cols) if target_cols else []

        sklearn_kwargs = {k: v for k, v in self.model_dump(exclude={"model", "model_class"}).items() if v is not None}
        model = self.model_class(**sklearn_kwargs)

        return SklearnRegressorWrapper(
            model=model,
            input_cols=input_cols,
            output_cols=output_cols,
            label_cols=label_cols,
        )


class BaseRegressionModelGridSearchConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    model: Literal[
        "GradientBoostingRegressor",
        "RandomForestRegressor",
        "LinearRegressionRegressor",
        "LassoRegressor",
        "ElasticNetRegressor",
        "HuberRegressor",
        "DecisionTreeRegressor",
        "NeuralNetworkRegressor",
    ]

    def get_optuna_grid_search_callable(self) -> Callable[[Trial], dict[str, Any]]:
        def suggest_config(trial: Trial) -> dict[str, Any]:
            d = {
                k: trial.suggest_categorical(k, v)
                for k, v in self.model_dump(exclude={"model"}).items()
                if v is not None
            }
            d["model"] = self.model
            return d

        return suggest_config

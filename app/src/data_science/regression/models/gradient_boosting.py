from typing import Literal

from pydantic import Field
from sklearn.ensemble import GradientBoostingRegressor

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class GradientBoostingRegressorModel(BaseRegressionModel):
    model: Literal["GradientBoostingRegressor"] = Field(default="GradientBoostingRegressor")
    model_class: type[GradientBoostingRegressor] = Field(default=GradientBoostingRegressor)
    loss: Literal["squared_error", "absolute_error", "huber", "quantile"] = Field(default="squared_error")
    learning_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    n_estimators: int = Field(default=100, ge=1)
    subsample: float = Field(default=1.0, gt=0.0, le=1.0)
    criterion: Literal["friedman_mse", "squared_error"] = Field(default="friedman_mse")
    min_samples_split: int = Field(default=2, ge=2)
    min_samples_leaf: int = Field(default=1, ge=1)
    min_weight_fraction_leaf: float = Field(default=0.0, ge=0.0, le=0.5)
    max_depth: int = Field(default=3, ge=1)
    min_impurity_decrease: float = Field(default=0.0, ge=0.0)
    init: str | None = Field(default=None)
    random_state: int | None = Field(default=None)
    max_features: int | float | Literal["sqrt", "log2"] | None = Field(default=None)
    alpha: float = Field(default=0.9, gt=0.0, lt=1.0)
    verbose: int = Field(default=0)
    max_leaf_nodes: int | None = Field(default=None, ge=2)
    warm_start: bool = Field(default=False)
    n_iter_no_change: int | None = Field(default=None)
    tol: float = Field(default=0.0001, ge=0.0)
    ccp_alpha: float = Field(default=0.0, ge=0.0)


class GradientBoostingRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["GradientBoostingRegressor"] = Field(default="GradientBoostingRegressor")
    loss: list[Literal["squared_error", "absolute_error", "huber", "quantile"]] | None = Field(default=None)
    learning_rate: list[float] | None = Field(default=None)
    n_estimators: list[int] | None = Field(default=None)
    subsample: list[float] | None = Field(default=None)
    criterion: list[Literal["friedman_mse", "squared_error"]] | None = Field(default=None)
    min_samples_split: list[int] | None = Field(default=None)
    min_samples_leaf: list[int] | None = Field(default=None)
    min_weight_fraction_leaf: list[float] | None = Field(default=None)
    max_depth: list[int] | None = Field(default=None)
    min_impurity_decrease: list[float] | None = Field(default=None)
    init: list[str] | None = Field(default=None)
    random_state: list[int] | None = Field(default=None)
    max_features: list[int | float | Literal["sqrt", "log2"]] | None = Field(default=None)
    alpha: list[float] | None = Field(default=None)
    verbose: list[int] | None = Field(default=None)
    max_leaf_nodes: list[int] | None = Field(default=None)
    warm_start: list[bool] | None = Field(default=None)
    n_iter_no_change: list[int] | None = Field(default=None)
    tol: list[float] | None = Field(default=None)
    ccp_alpha: list[float] | None = Field(default=None)

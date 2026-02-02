from typing import Literal, Optional, Union

from pydantic import Field
from snowflake.ml.modeling.ensemble.gradient_boosting_regressor import GradientBoostingRegressor

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class GradientBoostingRegressorModel(BaseRegressionModel):
    model: Literal["GradientBoostingRegressor"] = Field(default="GradientBoostingRegressor")
    model_class: GradientBoostingRegressor = Field(default=GradientBoostingRegressor)
    # see GradientBoostingRegressor.__init__
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
    init: Optional[str] = Field(default=None)
    random_state: Optional[int] = Field(default=None)
    max_features: Optional[Union[int, float, Literal["sqrt", "log2"]]] = Field(default=None)
    alpha: float = Field(default=0.9, gt=0.0, lt=1.0)
    verbose: int = Field(default=0)
    max_leaf_nodes: Optional[int] = Field(default=2, ge=2)
    warm_start: bool = Field(default=False)
    n_iter_no_change: Optional[int] = Field(default=None)
    tol: float = Field(default=0.0001, ge=0.0)
    ccp_alpha: float = Field(default=0.0, ge=0.0)


class GradientBoostingRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["GradientBoostingRegressor"] = Field(default="GradientBoostingRegressor")
    loss: Optional[list[Literal["squared_error", "absolute_error", "huber", "quantile"]]] = Field(default=None)
    learning_rate: Optional[list[float]] = Field(default=None)
    n_estimators: Optional[list[int]] = Field(default=None)
    subsample: Optional[list[float]] = Field(default=None)
    criterion: Optional[list[Literal["friedman_mse", "squared_error"]]] = Field(default=None)
    min_samples_split: Optional[list[int]] = Field(default=None)
    min_samples_leaf: Optional[list[int]] = Field(default=None)
    min_weight_fraction_leaf: Optional[list[float]] = Field(default=None)
    max_depth: Optional[list[int]] = Field(default=None)
    min_impurity_decrease: Optional[list[float]] = Field(default=None)
    init: Optional[list[str]] = Field(default=None)
    random_state: Optional[list[int]] = Field(default=None)
    max_features: Optional[list[Union[int, float, Literal["auto", "sqrt", "log2"]]]] = Field(default=None)
    alpha: Optional[list[float]] = Field(default=None)
    verbose: Optional[list[int]] = Field(default=None)
    max_leaf_nodes: Optional[list[int]] = Field(default=None)
    warm_start: Optional[list[bool]] = Field(default=None)
    n_iter_no_change: Optional[list[int]] = Field(default=None)
    tol: Optional[list[float]] = Field(default=None)
    ccp_alpha: Optional[list[float]] = Field(default=None)


# Example of config:
"""
model: GradientBoostingRegressor
loss: ["squared_error", "absolute_error", "huber", "quantile"]
learning_rate: [0.01, 0.05, 0.1, 0.2]
n_estimators: [100, 200, 300, 400]
"""

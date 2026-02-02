from typing import Literal, Optional, Union

from pydantic import Field
from snowflake.ml.modeling.linear_model.huber_regressor import HuberRegressor

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class HuberRegressorModel(BaseRegressionModel):
    model: Literal["HuberRegressor"] = Field(default="HuberRegressor")
    model_class: HuberRegressor = Field(default=HuberRegressor)
    epsilon: float = Field(default=1.35, ge=1.0, lt=10.0)
    alpha: float = Field(default=0.0001, ge=0.0)
    fit_intercept: bool = Field(default=True)
    max_iter: int = Field(default=1000, ge=1)
    tol: float = Field(default=1e-5, ge=0.0)


class HuberRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["HuberRegressor"] = Field(default="HuberRegressor")
    epsilon: Optional[list[float]] = Field(default=None)
    alpha: Optional[list[float]] = Field(default=None)
    fit_intercept: Optional[list[bool]] = Field(default=None)
    max_iter: Optional[list[int]] = Field(default=None)
    tol: Optional[list[float]] = Field(default=None)

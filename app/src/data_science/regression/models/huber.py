from typing import Literal

from pydantic import Field
from sklearn.linear_model import HuberRegressor

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class HuberRegressorModel(BaseRegressionModel):
    model: Literal["HuberRegressor"] = Field(default="HuberRegressor")
    model_class: type[HuberRegressor] = Field(default=HuberRegressor)
    epsilon: float = Field(default=1.35, ge=1.0, lt=10.0)
    alpha: float = Field(default=0.0001, ge=0.0)
    fit_intercept: bool = Field(default=True)
    max_iter: int = Field(default=1000, ge=1)
    tol: float = Field(default=1e-5, ge=0.0)


class HuberRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["HuberRegressor"] = Field(default="HuberRegressor")
    epsilon: list[float] | None = Field(default=None)
    alpha: list[float] | None = Field(default=None)
    fit_intercept: list[bool] | None = Field(default=None)
    max_iter: list[int] | None = Field(default=None)
    tol: list[float] | None = Field(default=None)

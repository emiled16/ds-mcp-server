from typing import Literal

from pydantic import Field
from sklearn.linear_model import ElasticNet

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class ElasticNetRegressorModel(BaseRegressionModel):
    model: Literal["ElasticNetRegressor"] = Field(default="ElasticNetRegressor")
    model_class: type[ElasticNet] = Field(default=ElasticNet)
    alpha: float = Field(default=1.0, ge=0.0)
    l1_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    fit_intercept: bool = Field(default=True)
    max_iter: int = Field(default=1000, ge=1)
    tol: float = Field(default=0.0001, ge=0.0)
    warm_start: bool = Field(default=False)
    selection: Literal["cyclic", "random"] = Field(default="cyclic")


class ElasticNetRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["ElasticNetRegressor"] = Field(default="ElasticNetRegressor")
    alpha: list[float] | None = Field(default=None)
    l1_ratio: list[float] | None = Field(default=None)
    max_iter: list[int] | None = Field(default=None)
    tol: list[float] | None = Field(default=None)
    fit_intercept: list[bool] | None = Field(default=None)
    warm_start: list[bool] | None = Field(default=None)
    selection: list[Literal["cyclic", "random"]] | None = Field(default=None)

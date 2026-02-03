from typing import Literal

from pydantic import Field
from sklearn.linear_model import Lasso

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class LassoRegressorModel(BaseRegressionModel):
    model: Literal["LassoRegressor"] = Field(default="LassoRegressor")
    model_class: type[Lasso] = Field(default=Lasso)
    alpha: float = Field(default=1.0, ge=0.0)
    fit_intercept: bool = Field(default=True)
    max_iter: int = Field(default=1000, ge=1)
    tol: float = Field(default=0.0001, ge=0.0)


class LassoRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["LassoRegressor"] = Field(default="LassoRegressor")
    alpha: list[float] | None = Field(default=None)
    fit_intercept: list[bool] | None = Field(default=None)
    max_iter: list[int] | None = Field(default=None)
    tol: list[float] | None = Field(default=None)

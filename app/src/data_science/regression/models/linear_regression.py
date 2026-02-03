from typing import Literal

from pydantic import Field
from sklearn.linear_model import LinearRegression

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class LinearRegressionRegressorModel(BaseRegressionModel):
    model: Literal["LinearRegressionRegressor"] = Field(default="LinearRegressionRegressor")
    model_class: type[LinearRegression] = Field(default=LinearRegression)
    fit_intercept: bool = Field(default=True)


class LinearRegressionRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["LinearRegressionRegressor"] = Field(default="LinearRegressionRegressor")
    fit_intercept: list[bool] | None = Field(default=None)

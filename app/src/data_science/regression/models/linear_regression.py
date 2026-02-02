from typing import Literal, Optional, Union

from pydantic import Field
from snowflake.ml.modeling.linear_model.linear_regression import LinearRegression

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class LinearRegressionRegressorModel(BaseRegressionModel):
    model: Literal["LinearRegressionRegressor"] = Field(default="LinearRegressionRegressor")
    model_class: LinearRegression = Field(default=LinearRegression)
    fit_intercept: bool = Field(default=True)


class LinearRegressionRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["LinearRegressionRegressor"] = Field(default="LinearRegressionRegressor")
    fit_intercept: Optional[list[bool]] = Field(default=None)

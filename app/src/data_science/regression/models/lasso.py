from typing import Literal, Optional, Union

from pydantic import Field
from snowflake.ml.modeling.linear_model.lasso import Lasso

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class LassoRegressorModel(BaseRegressionModel):
    model: Literal["LassoRegressor"] = Field(default="LassoRegressor")
    model_class: Lasso = Field(default=Lasso)
    alpha: float = Field(default=1.0, ge=0.0)
    fit_intercept: bool = Field(default=True)
    max_iter: int = Field(default=1000, ge=1)
    tol: float = Field(default=0.0001, ge=0.0)


class LassoRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["LassoRegressor"] = Field(default="LassoRegressor")
    alpha: Optional[list[float]] = Field(default=None)
    fit_intercept: Optional[list[bool]] = Field(default=None)
    max_iter: Optional[list[int]] = Field(default=None)
    tol: Optional[list[float]] = Field(default=None)

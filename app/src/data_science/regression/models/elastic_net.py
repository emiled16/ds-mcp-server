from typing import Literal, Optional, Union

from pydantic import Field
from snowflake.ml.modeling.linear_model.elastic_net import ElasticNet

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class ElasticNetRegressorModel(BaseRegressionModel):
    model: Literal["ElasticNetRegressor"] = Field(default="ElasticNetRegressor")
    model_class: ElasticNet = Field(default=ElasticNet)
    alpha: float = Field(default=1.0, ge=0.0)
    l1_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    fit_intercept: bool = Field(default=True)
    max_iter: int = Field(default=1000, ge=1)
    tol: float = Field(default=0.0001, ge=0.0)
    warm_start: bool = Field(default=False)
    selection: Literal["cyclic", "random"] = Field(default="random")


class ElasticNetRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["ElasticNetRegressor"] = Field(default="ElasticNetRegressor")
    alpha: Optional[list[float]] = Field(default=None)
    l1_ratio: Optional[list[float]] = Field(default=None)
    max_iter: Optional[list[int]] = Field(default=None)
    tol: Optional[list[float]] = Field(default=None)
    fit_intercept: Optional[list[bool]] = Field(default=None)
    warm_start: Optional[list[bool]] = Field(default=None)
    selection: Optional[list[Literal["cyclic", "random"]]] = Field(default=None)

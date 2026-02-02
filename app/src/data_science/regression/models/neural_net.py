from typing import Literal, Optional, Union

from pydantic import Field
from snowflake.ml.modeling.neural_network.mlp_regressor import MLPRegressor

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class NeuralNetworkRegressorModel(BaseRegressionModel):
    model: Literal["NeuralNetworkRegressor"] = Field(default="NeuralNetworkRegressor")
    model_class: MLPRegressor = Field(default=MLPRegressor)
    activation: Literal["identity", "logistic", "tanh", "relu"] = Field(default="relu")
    solver: Literal["lbfgs", "sgd", "adam"] = Field(default="adam")
    alpha: float = Field(default=0.0001, ge=0.0)
    batch_size: Union[int, Literal["auto"]] = Field(default="auto")
    learning_rate: Literal["constant", "invscaling", "adaptive"] = Field(default="constant")
    learning_rate_init: float = Field(default=0.1, gt=0.0)
    power_t: float = Field(default=0.5, ge=0.0)
    max_iter: int = Field(default=200, ge=1)
    tol: float = Field(default=1e-4, ge=0.0)
    momentum: float = Field(default=0.9, ge=0.0, lt=1.0)
    nesterovs_momentum: bool = Field(default=True)
    early_stopping: bool = Field(default=False)
    beta_1: float = Field(default=0.1, ge=0.0, lt=1.0)
    beta_2: float = Field(default=0.1, ge=0.0, lt=1.0)
    epsilon: float = Field(default=0.1, gt=0.0, lt=1.0)
    n_iter_no_change: int = Field(default=10, ge=1)
    warm_start: bool = Field(default=False)


class NeuralNetworkRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["NeuralNetworkRegressor"] = Field(default="NeuralNetworkRegressor")
    activation: Optional[list[Literal["identity", "logistic", "tanh", "relu"]]] = Field(default=None)
    solver: Optional[list[Literal["lbfgs", "sgd", "adam"]]] = Field(default=None)
    alpha: Optional[list[float]] = Field(default=None)
    batch_size: Optional[list[Union[int, Literal["auto"]]]] = Field(default=None)
    learning_rate: Optional[list[Literal["constant", "invscaling", "adaptive"]]] = Field(default=None)
    learning_rate_init: Optional[list[float]] = Field(default=None)
    power_t: Optional[list[float]] = Field(default=None)
    max_iter: Optional[list[int]] = Field(default=None)
    tol: Optional[list[float]] = Field(default=None)
    momentum: Optional[list[float]] = Field(default=None)
    nesterovs_momentum: Optional[list[bool]] = Field(default=None)
    early_stopping: Optional[list[bool]] = Field(default=None)
    beta_1: Optional[list[float]] = Field(default=None)
    beta_2: Optional[list[float]] = Field(default=None)
    epsilon: Optional[list[float]] = Field(default=None)
    n_iter_no_change: Optional[list[int]] = Field(default=None)
    warm_start: Optional[list[bool]] = Field(default=None)

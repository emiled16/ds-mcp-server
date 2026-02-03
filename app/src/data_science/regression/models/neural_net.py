from typing import Literal

from pydantic import Field
from sklearn.neural_network import MLPRegressor

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class NeuralNetworkRegressorModel(BaseRegressionModel):
    model: Literal["NeuralNetworkRegressor"] = Field(default="NeuralNetworkRegressor")
    model_class: type[MLPRegressor] = Field(default=MLPRegressor)
    activation: Literal["identity", "logistic", "tanh", "relu"] = Field(default="relu")
    solver: Literal["lbfgs", "sgd", "adam"] = Field(default="adam")
    alpha: float = Field(default=0.0001, ge=0.0)
    batch_size: int | Literal["auto"] = Field(default="auto")
    learning_rate: Literal["constant", "invscaling", "adaptive"] = Field(default="constant")
    learning_rate_init: float = Field(default=0.001, gt=0.0)
    power_t: float = Field(default=0.5, ge=0.0)
    max_iter: int = Field(default=200, ge=1)
    tol: float = Field(default=1e-4, ge=0.0)
    momentum: float = Field(default=0.9, ge=0.0, lt=1.0)
    nesterovs_momentum: bool = Field(default=True)
    early_stopping: bool = Field(default=False)
    beta_1: float = Field(default=0.9, ge=0.0, lt=1.0)
    beta_2: float = Field(default=0.999, ge=0.0, lt=1.0)
    epsilon: float = Field(default=1e-8, gt=0.0, lt=1.0)
    n_iter_no_change: int = Field(default=10, ge=1)
    warm_start: bool = Field(default=False)


class NeuralNetworkRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["NeuralNetworkRegressor"] = Field(default="NeuralNetworkRegressor")
    activation: list[Literal["identity", "logistic", "tanh", "relu"]] | None = Field(default=None)
    solver: list[Literal["lbfgs", "sgd", "adam"]] | None = Field(default=None)
    alpha: list[float] | None = Field(default=None)
    batch_size: list[int | Literal["auto"]] | None = Field(default=None)
    learning_rate: list[Literal["constant", "invscaling", "adaptive"]] | None = Field(default=None)
    learning_rate_init: list[float] | None = Field(default=None)
    power_t: list[float] | None = Field(default=None)
    max_iter: list[int] | None = Field(default=None)
    tol: list[float] | None = Field(default=None)
    momentum: list[float] | None = Field(default=None)
    nesterovs_momentum: list[bool] | None = Field(default=None)
    early_stopping: list[bool] | None = Field(default=None)
    beta_1: list[float] | None = Field(default=None)
    beta_2: list[float] | None = Field(default=None)
    epsilon: list[float] | None = Field(default=None)
    n_iter_no_change: list[int] | None = Field(default=None)
    warm_start: list[bool] | None = Field(default=None)

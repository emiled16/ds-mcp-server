from typing import Literal

from pydantic import Field
from sklearn.tree import DecisionTreeRegressor

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class DecisionTreeRegressorModel(BaseRegressionModel):
    model: Literal["DecisionTreeRegressor"] = Field(default="DecisionTreeRegressor")
    model_class: type[DecisionTreeRegressor] = Field(default=DecisionTreeRegressor)
    criterion: Literal["squared_error", "friedman_mse", "absolute_error", "poisson"] = Field(default="squared_error")
    max_depth: int | None = Field(default=None)
    min_samples_split: int = Field(default=2, ge=1)
    min_samples_leaf: int = Field(default=1, ge=1)
    min_weight_fraction_leaf: float = Field(default=0.0, ge=0.0, le=0.5)
    max_features: int | float | Literal["sqrt", "log2"] | None = Field(default=None)
    ccp_alpha: float = Field(default=0.0, ge=0.0)


class DecisionTreeRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["DecisionTreeRegressor"] = Field(default="DecisionTreeRegressor")
    criterion: list[Literal["squared_error", "friedman_mse", "absolute_error", "poisson"]] | None = Field(default=None)
    max_depth: list[int] | None = Field(default=None)
    min_samples_split: list[int] | None = Field(default=None)
    min_samples_leaf: list[int] | None = Field(default=None)
    max_features: list[int | float | Literal["sqrt", "log2"]] | None = Field(default=None)

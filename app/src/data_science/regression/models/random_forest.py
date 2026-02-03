from typing import Literal

import numpy as np
from pydantic import Field
from sklearn.ensemble import RandomForestRegressor

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class RandomForestRegressorModel(BaseRegressionModel):
    model: Literal["RandomForestRegressor"] = Field(default="RandomForestRegressor")
    model_class: type[RandomForestRegressor] = Field(default=RandomForestRegressor)
    n_estimators: int = Field(default=100, ge=1)
    criterion: Literal["squared_error", "absolute_error", "friedman_mse"] = Field(default="squared_error")
    max_depth: int | None = Field(default=None, ge=1)
    min_samples_split: int = Field(default=2, ge=2)
    min_samples_leaf: int = Field(default=1, ge=1)
    min_weight_fraction_leaf: float = Field(default=0.0, ge=0.0, le=0.5)
    max_features: int | float | Literal["sqrt", "log2"] | None = Field(default=None)
    max_leaf_nodes: int | None = Field(default=None, ge=2)
    min_impurity_decrease: float = Field(default=0.0, ge=0.0)
    bootstrap: bool = Field(default=True)
    oob_score: bool = Field(default=False)
    n_jobs: int | None = Field(default=None)
    random_state: int | None = Field(default=None)
    verbose: int = Field(default=0)
    warm_start: bool = Field(default=False)
    ccp_alpha: float = Field(default=0.0, ge=0.0)
    max_samples: int | float | None = Field(default=None)
    monotonic_cst: np.ndarray | None = Field(default=None)


class RandomForestRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["RandomForestRegressor"] = Field(default="RandomForestRegressor")
    n_estimators: list[int] | None = Field(default=None)
    criterion: list[Literal["squared_error", "absolute_error", "friedman_mse"]] | None = Field(default=None)
    max_depth: list[int] | None = Field(default=None)
    min_samples_split: list[int] | None = Field(default=None)
    min_samples_leaf: list[int] | None = Field(default=None)
    min_weight_fraction_leaf: list[float] | None = Field(default=None)
    max_features: list[int | float | Literal["sqrt", "log2"]] | None = Field(default=None)
    max_leaf_nodes: list[int] | None = Field(default=None)
    min_impurity_decrease: list[float] | None = Field(default=None)
    bootstrap: list[bool] | None = Field(default=None)
    oob_score: list[bool] | None = Field(default=None)
    n_jobs: list[int] | None = Field(default=None)
    random_state: list[int] | None = Field(default=None)
    verbose: list[int] | None = Field(default=None)
    warm_start: list[bool] | None = Field(default=None)
    ccp_alpha: list[float] | None = Field(default=None)
    max_samples: list[int | float] | None = Field(default=None)
    monotonic_cst: list[np.ndarray] | None = Field(default=None)

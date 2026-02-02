from typing import Literal, Optional, Union

import numpy as np
from pydantic import Field
from snowflake.ml.modeling.ensemble.random_forest_regressor import RandomForestRegressor

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class RandomForestRegressorModel(BaseRegressionModel):
    model: Literal["RandomForestRegressor"] = Field(default="RandomForestRegressor")
    model_class: RandomForestRegressor = Field(default=RandomForestRegressor)
    # see RandomForestRegressor.__init__
    n_estimators: int = Field(default=100, ge=1)
    criterion: Literal["squared_error", "absolute_error", "friedman_mse"] = Field(default="squared_error")
    max_depth: Optional[int] = Field(default=None, ge=1)
    min_samples_split: int = Field(default=2, ge=2)
    min_samples_leaf: int = Field(default=1, ge=1)
    min_weight_fraction_leaf: float = Field(default=0.0, ge=0.0, le=0.5)
    max_features: Optional[Union[int, float, Literal["sqrt", "log2"]]] = Field(default=None)
    max_leaf_nodes: Optional[int] = Field(default=2, ge=2)
    min_impurity_decrease: float = Field(default=0.0, ge=0.0)
    bootstrap: bool = Field(default=True)
    oob_score: bool = Field(default=False)
    n_jobs: Optional[int] = Field(default=None)
    random_state: Optional[int] = Field(default=None)
    verbose: int = Field(default=0)
    warm_start: bool = Field(default=False)
    ccp_alpha: float = Field(default=0.0, ge=0.0)
    max_samples: Optional[Union[int, float]] = Field(default=0.01)
    monotonic_cst: Optional[np.ndarray] = Field(default=None)


class RandomForestRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["RandomForestRegressor"] = Field(default="RandomForestRegressor")
    n_estimators: Optional[list[int]] = Field(default=None)
    criterion: Optional[list[Literal["squared_error", "absolute_error", "friedman_mse"]]] = Field(default=None)
    max_depth: Optional[list[int]] = Field(default=None)
    min_samples_split: Optional[list[int]] = Field(default=None)
    min_samples_leaf: Optional[list[int]] = Field(default=None)
    min_weight_fraction_leaf: Optional[list[float]] = Field(default=None)
    max_features: Optional[list[Union[int, float, Literal["sqrt", "log2"]]]] = Field(default=None)
    max_leaf_nodes: Optional[list[int]] = Field(default=None)
    min_impurity_decrease: Optional[list[float]] = Field(default=None)
    bootstrap: Optional[list[bool]] = Field(default=None)
    oob_score: Optional[list[bool]] = Field(default=None)
    n_jobs: Optional[list[int]] = Field(default=None)
    random_state: Optional[list[int]] = Field(default=None)
    verbose: Optional[list[int]] = Field(default=None)
    warm_start: Optional[list[bool]] = Field(default=None)
    ccp_alpha: Optional[list[float]] = Field(default=None)
    max_samples: Optional[list[Union[int, float]]] = Field(default=None)
    monotonic_cst: Optional[list[np.ndarray]] = Field(default=None)

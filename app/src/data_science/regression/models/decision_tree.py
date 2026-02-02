from typing import Literal, Optional, Union

from pydantic import Field
from snowflake.ml.modeling.tree.decision_tree_regressor import DecisionTreeRegressor

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class DecisionTreeRegressorModel(BaseRegressionModel):
    model: Literal["DecisionTreeRegressor"] = Field(default="DecisionTreeRegressor")
    model_class: DecisionTreeRegressor = Field(default=DecisionTreeRegressor)
    criterion: Literal["squared_error", "friedman_mse", "absolute_error", "poisson"] = Field(default="squared_error")
    max_depth: Optional[int] = Field(default=None)
    min_samples_split: int = Field(default=2, ge=1)
    min_samples_leaf: int = Field(default=1, ge=1)
    min_weight_fraction_leaf: float = Field(default=0.0, ge=0.0, le=0.5)
    max_features: Optional[Union[int, float, Literal["sqrt", "log2"]]] = Field(default=None)
    ccp_alpha: float = Field(default=0.0, ge=0.0)


class DecisionTreeRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["DecisionTreeRegressor"] = Field(default="DecisionTreeRegressor")
    criterion: Optional[list[Literal["squared_error", "friedman_mse", "absolute_error", "poisson"]]] = Field(
        default=None
    )
    max_depth: Optional[list[int]] = Field(default=None)
    min_samples_split: Optional[list[int]] = Field(default=None)
    min_samples_leaf: Optional[list[int]] = Field(default=None)
    max_features: Optional[list[Union[int, float, Literal["sqrt", "log2"]]]] = Field(default=None)

from typing import Literal, Optional

from pydantic import Field
from snowflake.ml.modeling.xgboost import XGBRegressor

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class XGBRegressorModel(BaseRegressionModel):
    model: Literal["XGBRegressor"] = Field(default="XGBRegressor")
    model_class: XGBRegressor = Field(default=XGBRegressor)
    n_estimators: int = Field(default=100, ge=1)
    max_depth: int = Field(default=3, ge=1)
    learning_rate: float = Field(default=0.1, ge=0.0)
    subsample: float = Field(default=1.0, ge=0.0, le=1.0)
    colsample_bytree: float = Field(default=1.0, ge=0.0, le=1.0)
    gamma: float = Field(default=0.0, ge=0.0)
    reg_alpha: float = Field(default=0.0, ge=0.0)
    reg_lambda: float = Field(default=1.0, ge=0.0)
    booster: Literal["gbtree", "gblinear", "dart"] = Field(default="gbtree")
    tree_method: Optional[str] = Field(default=None)
    random_state: Optional[int] = Field(default=None)


class XGBRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["XGBRegressor"] = Field(default="XGBRegressor")
    n_estimators: Optional[list[int]] = Field(default=None)
    max_depth: Optional[list[int]] = Field(default=None)
    learning_rate: Optional[list[float]] = Field(default=None)
    subsample: Optional[list[float]] = Field(default=None)
    colsample_bytree: Optional[list[float]] = Field(default=None)
    gamma: Optional[list[float]] = Field(default=None)
    reg_alpha: Optional[list[float]] = Field(default=None)
    reg_lambda: Optional[list[float]] = Field(default=None)
    booster: Optional[list[Literal["gbtree", "gblinear", "dart"]]] = Field(default=None)
    tree_method: Optional[list[str]] = Field(default=None)
    random_state: Optional[list[int]] = Field(default=None)

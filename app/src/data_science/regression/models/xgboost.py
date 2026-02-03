from typing import Literal

from pydantic import Field
from xgboost import XGBRegressor

from src.data_science.regression.models.base import BaseRegressionModel, BaseRegressionModelGridSearchConfig


class XGBRegressorModel(BaseRegressionModel):
    model: Literal["XGBRegressor"] = Field(default="XGBRegressor")
    model_class: type[XGBRegressor] = Field(default=XGBRegressor)
    n_estimators: int = Field(default=100, ge=1)
    max_depth: int = Field(default=3, ge=1)
    learning_rate: float = Field(default=0.1, ge=0.0)
    subsample: float = Field(default=1.0, ge=0.0, le=1.0)
    colsample_bytree: float = Field(default=1.0, ge=0.0, le=1.0)
    gamma: float = Field(default=0.0, ge=0.0)
    reg_alpha: float = Field(default=0.0, ge=0.0)
    reg_lambda: float = Field(default=1.0, ge=0.0)
    booster: Literal["gbtree", "gblinear", "dart"] = Field(default="gbtree")
    tree_method: str | None = Field(default=None)
    random_state: int | None = Field(default=None)


class XGBRegressorGridSearchConfig(BaseRegressionModelGridSearchConfig):
    model: Literal["XGBRegressor"] = Field(default="XGBRegressor")
    n_estimators: list[int] | None = Field(default=None)
    max_depth: list[int] | None = Field(default=None)
    learning_rate: list[float] | None = Field(default=None)
    subsample: list[float] | None = Field(default=None)
    colsample_bytree: list[float] | None = Field(default=None)
    gamma: list[float] | None = Field(default=None)
    reg_alpha: list[float] | None = Field(default=None)
    reg_lambda: list[float] | None = Field(default=None)
    booster: list[Literal["gbtree", "gblinear", "dart"]] | None = Field(default=None)
    tree_method: list[str] | None = Field(default=None)
    random_state: list[int] | None = Field(default=None)

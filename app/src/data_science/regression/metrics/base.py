from abc import ABC, abstractmethod
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel

from src.data_science.snowflake_optional import SNOWFLAKE_AVAILABLE, SnowparkDataFrame


class BaseMetric(BaseModel, ABC):
    metric: Literal["mean_squared_error", "d2_pinball_score", "mean_absolute_percentage_error", "r2_score"]

    @abstractmethod
    def _evaluate_local(
        self,
        dataset: pd.DataFrame,
        y_true_col_names: str | list[str],
        y_pred_col_names: str | list[str],
    ):
        pass

    @abstractmethod
    def _evaluate_snowflake(
        self,
        dataset: Any,
        y_true_col_names: str | list[str],
        y_pred_col_names: str | list[str],
    ):
        pass

    def evaluate(
        self,
        dataset: pd.DataFrame | Any,
        y_true_col_names: str | list[str],
        y_pred_col_names: str | list[str],
    ) -> float | None:
        if isinstance(dataset, pd.DataFrame):
            return self._evaluate_local(dataset, y_true_col_names, y_pred_col_names)
        if SNOWFLAKE_AVAILABLE and SnowparkDataFrame is not None and isinstance(dataset, SnowparkDataFrame):
            return self._evaluate_snowflake(dataset, y_true_col_names, y_pred_col_names)
        raise ValueError(f"Invalid dataset type: {type(dataset)}")

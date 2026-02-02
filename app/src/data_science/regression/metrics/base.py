from abc import ABC, abstractmethod
from typing import Literal, Optional, Union

import pandas as pd
from pydantic import BaseModel
from snowflake import snowpark


class BaseMetric(BaseModel, ABC):
    metric: Literal["mean_squared_error", "d2_pinball_score", "mean_absolute_percentage_error", "r2_score"]

    @abstractmethod
    def _evaluate_local(
        self,
        dataset: pd.DataFrame,
        y_true_col_names: Union[str, list[str]],
        y_pred_col_names: Union[str, list[str]],
    ):
        pass

    @abstractmethod
    def _evaluate_snowflake(
        self,
        dataset: snowpark.DataFrame,
        y_true_col_names: Union[str, list[str]],
        y_pred_col_names: Union[str, list[str]],
    ):
        pass

    def evaluate(
        self,
        dataset: Union[pd.DataFrame, snowpark.DataFrame],
        y_true_col_names: Union[str, list[str]],
        y_pred_col_names: Union[str, list[str]],
    ) -> Optional[float]:
        if isinstance(dataset, pd.DataFrame):
            return self._evaluate_local(dataset, y_true_col_names, y_pred_col_names)
        if isinstance(dataset, snowpark.DataFrame):
            return self._evaluate_snowflake(dataset, y_true_col_names, y_pred_col_names)
        raise ValueError(f"Invalid dataset type: {type(dataset)}")

from typing import Literal, Union

import pandas as pd
import sklearn.metrics as sklearn_metrics
import snowflake.ml.modeling.metrics.regression as snowpark_metrics
from snowflake import snowpark

from src.data_science.regression.metrics.base import BaseMetric


class MeanSquaredError(BaseMetric):
    metric: Literal["mean_squared_error"] = "mean_squared_error"

    def _evaluate_local(
        self,
        dataset: pd.DataFrame,
        y_true_col_names: Union[str, list[str]],
        y_pred_col_names: Union[str, list[str]],
    ):
        return sklearn_metrics.mean_squared_error(
            y_true=dataset[y_true_col_names],
            y_pred=dataset[y_pred_col_names],
        )

    def _evaluate_snowflake(
        self,
        dataset: snowpark.DataFrame,
        y_true_col_names: Union[str, list[str]],
        y_pred_col_names: Union[str, list[str]],
    ):
        return snowpark_metrics.mean_squared_error(
            df=dataset,
            y_true_col_names=y_true_col_names,
            y_pred_col_names=y_pred_col_names,
        )

from typing import Any, Literal

import pandas as pd
import sklearn.metrics as sklearn_metrics

from src.data_science.regression.metrics.base import BaseMetric
from src.data_science.snowflake_optional import snowpark_metrics_regression as snowpark_metrics


class MeanAbsolutePercentageError(BaseMetric):
    metric: Literal["mean_absolute_percentage_error"] = "mean_absolute_percentage_error"

    def _evaluate_local(
        self,
        dataset: pd.DataFrame,
        y_true_col_names: str | list[str],
        y_pred_col_names: str | list[str],
    ):
        return sklearn_metrics.mean_absolute_percentage_error(
            y_true=dataset[y_true_col_names],
            y_pred=dataset[y_pred_col_names],
        )

    def _evaluate_snowflake(
        self,
        dataset: Any,
        y_true_col_names: str | list[str],
        y_pred_col_names: str | list[str],
    ):
        return snowpark_metrics.mean_absolute_percentage_error(
            df=dataset,
            y_true_col_names=y_true_col_names,
            y_pred_col_names=y_pred_col_names,
        )

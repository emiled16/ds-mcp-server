from typing import Literal, Union

import pandas as pd
import snowflake.snowpark.functions as f
from snowflake import snowpark

from src.data_science.regression.metrics.base import BaseMetric


class WeightedMeanAbsolutePercentageError(BaseMetric):
    metric: Literal["weighted_mean_absolute_percentage_error"] = "weighted_mean_absolute_percentage_error"

    def _evaluate_local(
        self,
        dataset: pd.DataFrame,
        y_true_col_names: Union[str, list[str]],
        y_pred_col_names: Union[str, list[str]],
    ) -> float:
        return (
            dataset.apply(lambda row: row[y_true_col_names] - row[y_pred_col_names], axis=1).abs().sum()
            / dataset[y_true_col_names].abs().sum()
        )

    def _evaluate_snowflake(
        self,
        dataset: snowpark.DataFrame,
        y_true_col_names: Union[str, list[str]],
        y_pred_col_names: Union[str, list[str]],
    ) -> float:
        assert isinstance(y_true_col_names, str), "y_true_col_names must be a string"
        assert isinstance(y_pred_col_names, str), "y_pred_col_names must be a string"
        return (
            dataset.with_column(
                "weighted_mape",
                f.sum(f.abs(f.col(y_true_col_names) - f.col(y_pred_col_names))) / f.sum(f.abs(f.col(y_true_col_names))),
            )
            .select("weighted_mape")
            .collect()[0][0]
        )

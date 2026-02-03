from typing import Literal

import pandas as pd

from src.data_science.regression.metrics.base import BaseMetric
from src.data_science.snowflake_optional import F as f


class WeightedMeanAbsolutePercentageError(BaseMetric):
    metric: Literal["weighted_mean_absolute_percentage_error"] = "weighted_mean_absolute_percentage_error"

    def _evaluate_local(
        self,
        dataset: pd.DataFrame,
        y_true_col_names: str | list[str],
        y_pred_col_names: str | list[str],
    ) -> float:
        return (
            dataset.apply(lambda row: row[y_true_col_names] - row[y_pred_col_names], axis=1).abs().sum()
            / dataset[y_true_col_names].abs().sum()
        )

    def _evaluate_snowflake(
        self,
        dataset: Any,
        y_true_col_names: str | list[str],
        y_pred_col_names: str | list[str],
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

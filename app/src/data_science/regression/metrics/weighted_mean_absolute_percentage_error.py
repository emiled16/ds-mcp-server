from typing import Literal

import pandas as pd

from src.data_science.regression.metrics.base import BaseMetric


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

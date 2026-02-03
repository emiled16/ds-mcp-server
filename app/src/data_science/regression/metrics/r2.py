from typing import Any, Literal

import pandas as pd
import sklearn.metrics as sklearn_metrics

from src.data_science.regression.metrics.base import BaseMetric
from src.data_science.snowflake_optional import snowpark_metrics_regression as snowpark_metrics


class R2Score(BaseMetric):
    metric: Literal["r2_score"] = "r2_score"
    sample_weight: str | None = None

    def _evaluate_local(
        self,
        dataset: pd.DataFrame,
        y_true_col_names: str | list[str],
        y_pred_col_names: str | list[str],
    ):
        return sklearn_metrics.r2_score(
            y_true=dataset[y_true_col_names],
            y_pred=dataset[y_pred_col_names],
        )

    def _evaluate_snowflake(
        self,
        dataset: Any,
        y_true_col_names: str | list[str],
        y_pred_col_names: str | list[str],
    ):
        assert isinstance(y_true_col_names, str), "y_true_col_names must be a string"
        assert isinstance(y_pred_col_names, str), "y_pred_col_names must be a string"
        return snowpark_metrics.r2_score(
            df=dataset,
            y_true_col_name=y_true_col_names,
            y_pred_col_name=y_pred_col_names,
        )

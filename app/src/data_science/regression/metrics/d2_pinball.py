from typing import Literal

import pandas as pd
import sklearn.metrics as sklearn_metrics

from src.data_science.regression.metrics.base import BaseMetric
from src.data_science.snowflake_optional import snowpark_metrics_regression as snowpark_metrics


class D2PinballScore(BaseMetric):
    metric: Literal["d2_pinball_score"] = "d2_pinball_score"
    sample_weight: str | None = None
    alpha: float = 0.5

    def _evaluate_local(
        self,
        dataset: pd.DataFrame,
        y_true_col_names: str | list[str],
        y_pred_col_names: str | list[str],
    ):
        return sklearn_metrics.d2_pinball_score(
            y_true=dataset[y_true_col_names],
            y_pred=dataset[y_pred_col_names],
            sample_weight=self.sample_weight,
            alpha=self.alpha,
        )

    def _evaluate_snowflake(
        self,
        dataset: Any,
        y_true_col_names: str | list[str],
        y_pred_col_names: str | list[str],
    ):
        return snowpark_metrics.d2_pinball_score(
            df=dataset,
            y_true_col_names=y_true_col_names,
            y_pred_col_names=y_pred_col_names,
            sample_weight_col_name=self.sample_weight,
            alpha=self.alpha,
        )

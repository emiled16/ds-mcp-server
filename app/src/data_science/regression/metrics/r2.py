from typing import Literal

import pandas as pd
import sklearn.metrics as sklearn_metrics

from src.data_science.regression.metrics.base import BaseMetric


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

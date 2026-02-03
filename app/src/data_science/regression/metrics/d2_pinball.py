from typing import Literal

import pandas as pd
import sklearn.metrics as sklearn_metrics

from src.data_science.regression.metrics.base import BaseMetric


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

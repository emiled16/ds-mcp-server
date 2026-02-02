from typing import List, Literal, Optional, Union

import pandas as pd
import sklearn.metrics as sklearn_metrics
import snowflake.ml.modeling.metrics.regression as snowpark_metrics
from snowflake import snowpark

from src.data_science.regression.metrics.base import BaseMetric


class D2PinballScore(BaseMetric):
    metric: Literal["d2_pinball_score"] = "d2_pinball_score"
    sample_weight: Optional[str] = None
    alpha: float = 0.5

    def _evaluate_local(
        self,
        dataset: pd.DataFrame,
        y_true_col_names: Union[str, List[str]],
        y_pred_col_names: Union[str, List[str]],
    ):
        return sklearn_metrics.d2_pinball_score(
            y_true=dataset[y_true_col_names],
            y_pred=dataset[y_pred_col_names],
            sample_weight=self.sample_weight,
            alpha=self.alpha,
        )

    def _evaluate_snowflake(
        self,
        dataset: snowpark.DataFrame,
        y_true_col_names: Union[str, List[str]],
        y_pred_col_names: Union[str, List[str]],
    ):
        return snowpark_metrics.d2_pinball_score(
            df=dataset,
            y_true_col_names=y_true_col_names,
            y_pred_col_names=y_pred_col_names,
            sample_weight_col_name=self.sample_weight,
            alpha=self.alpha,
        )

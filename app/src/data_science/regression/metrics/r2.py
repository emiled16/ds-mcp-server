from typing import Literal, Optional, Union

import pandas as pd
import sklearn.metrics as sklearn_metrics
import snowflake.ml.modeling.metrics.regression as snowpark_metrics
from snowflake import snowpark

from src.data_science.regression.metrics.base import BaseMetric


class R2Score(BaseMetric):
    metric: Literal["r2_score"] = "r2_score"
    sample_weight: Optional[str] = None

    def _evaluate_local(
        self,
        dataset: pd.DataFrame,
        y_true_col_names: Union[str, list[str]],
        y_pred_col_names: Union[str, list[str]],
    ):
        return sklearn_metrics.r2_score(
            y_true=dataset[y_true_col_names],
            y_pred=dataset[y_pred_col_names],
        )

    def _evaluate_snowflake(
        self,
        dataset: snowpark.DataFrame,
        y_true_col_names: Union[str, list[str]],
        y_pred_col_names: Union[str, list[str]],
    ):
        assert isinstance(y_true_col_names, str), "y_true_col_names must be a string"
        assert isinstance(y_pred_col_names, str), "y_pred_col_names must be a string"
        return snowpark_metrics.r2_score(
            df=dataset,
            y_true_col_name=y_true_col_names,
            y_pred_col_name=y_pred_col_names,
        )

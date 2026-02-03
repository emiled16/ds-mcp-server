from typing import Annotated, Any, Union

import pandas as pd
from pydantic import BaseModel, Field

from src.data_science.regression.metrics.absolute_net_error import AbsoluteNetError
from src.data_science.regression.metrics.d2_pinball import D2PinballScore
from src.data_science.regression.metrics.mean_absolute_percentage_error import MeanAbsolutePercentageError
from src.data_science.regression.metrics.mean_squared_error import MeanSquaredError
from src.data_science.regression.metrics.r2 import R2Score
from src.data_science.regression.metrics.weighted_mean_absolute_percentage_error import (
    WeightedMeanAbsolutePercentageError,
)

Metric = Annotated[
    MeanSquaredError
    | D2PinballScore
    | MeanAbsolutePercentageError
    | R2Score
    | WeightedMeanAbsolutePercentageError
    | AbsoluteNetError,
    Field(discriminator="metric"),
]


class Scorer(BaseModel):
    metrics: list[Metric]

    def evaluate(
        self,
        dataset: pd.DataFrame | Any,
        y_true_col_names: str | list[str],
        y_pred_col_names: str | list[str],
    ):
        results = {}
        for metric in self.metrics:
            results[metric.metric] = metric.evaluate(dataset, y_true_col_names, y_pred_col_names)
        return results

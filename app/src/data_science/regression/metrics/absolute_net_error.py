from typing import Literal

import pandas as pd

from src.data_science.regression.metrics.base import BaseMetric


class AbsoluteNetError(BaseMetric):
    metric: Literal["absolute_net_error"] = "absolute_net_error"

    def _evaluate_local(
        self,
        dataset: pd.DataFrame,
        y_true_col_names: str | list[str],
        y_pred_col_names: str | list[str],
        direction_col: str = "direction",
        date_col: str = "date",
    ):
        if len(y_true_col_names) > 0:
            y_true_col_name = y_true_col_names[0]

        if len(y_pred_col_names) > 0:
            y_pred_col_name = y_pred_col_names[0]

        df = dataset.groupby([date_col, direction_col]).agg({y_true_col_name: sum, y_pred_col_name: sum}).reset_index()
        df = df.assign(
            credit_actuals=lambda _d: _d.apply(
                lambda x: 0 if x[direction_col] == "OUT" else x[y_true_col_name], axis=1
            ),
            debit_actuals=lambda _d: _d.apply(lambda x: 0 if x[direction_col] == "IN" else x[y_true_col_name], axis=1),
            credit_forecasts=lambda _d: _d.apply(
                lambda x: 0 if x[direction_col] == "OUT" else x[y_pred_col_name], axis=1
            ),
            debit_forecasts=lambda _d: _d.apply(
                lambda x: 0 if x[direction_col] == "IN" else x[y_pred_col_name], axis=1
            ),
        )

        df = df.assign(
            net_actuals=lambda _d: _d.credit_actuals - _d.debit_actuals,
            net_forecasts=lambda _d: _d.credit_forecasts - _d.debit_forecasts,
        )

        df = df.assign(
            abs_net_error=lambda _d: (_d.net_actuals - _d.net_forecasts),
        )
        return df.abs_net_error.abs().mean()

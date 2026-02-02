from typing import Generator, Literal

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from pydantic import ConfigDict, Field

from src.data_science.ds_core.definitions.splitters.base import BaseSplitter


class TimeSeriesHoldout(BaseSplitter):
    """
    Split the dataset into train and test sets based on a time series backtest.
    If the timeseries is multi-dimensional, make sure all the timeseries have the same dates.
    dates are fetched globally, not per timeseries and then the split is done on the global dates.
    """

    model_config = ConfigDict(extra="forbid")
    method: Literal["timeseries-holdout"] = Field(default="timeseries-holdout")
    holdout_size: float | int = Field(
        description="size of the test set. if float, then it should be between 0 and 1. if it is an integer, "
        "represents the number of periods (periodicity) to keep for the test size"
    )
    periodicity: Literal["monthly"] = "monthly"
    date_column: str = Field(default="datetime")
    ascending: bool = Field(
        default=True,
        description="If True, split the dataset from the earliest date to the latest date."
        "If False, split in the reverse order.",
    )

    def split(self, dataset: pd.DataFrame) -> Generator[tuple[pd.Index, pd.Index], None, None]:
        """
        Split the dataset into train and test sets based on a time series holdout.
        """

        unique_dates = np.sort(dataset[self.date_column].unique())
        ordered_dates = unique_dates[::-1] if not self.ascending else unique_dates
        if isinstance(self.holdout_size, int):
            if self.holdout_size >= len(unique_dates):
                raise ValueError(
                    f"Holdout size is too big, choose a holdout size that is smaller than {len(unique_dates)} or a float between 0 and 1"
                )

            last_date = ordered_dates[-1]

            last_month = (
                pd.to_datetime(last_date).to_pydatetime() - relativedelta(months=self.holdout_size - 1)
            ).replace(day=1)

            split_index = -1
            for i, date in enumerate(ordered_dates):
                if pd.to_datetime(date).to_pydatetime() >= last_month:
                    split_index = i
                    break
        else:
            split_index = int(len(ordered_dates) * (1 - self.holdout_size))

        train_idx = dataset[dataset[self.date_column].isin(ordered_dates[:split_index])].index
        test_idx = dataset[dataset[self.date_column].isin(ordered_dates[split_index:])].index

        yield train_idx, test_idx

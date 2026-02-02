from typing import Annotated, Union

from pydantic import Field

from src.data_science.ds_core.definitions.splitters.holdout import Holdout
from src.data_science.ds_core.definitions.splitters.kfold import KFold
from src.data_science.ds_core.definitions.splitters.timeseries_backtest import TimeSeriesBacktest
from src.data_science.ds_core.definitions.splitters.timeseries_holdout import TimeSeriesHoldout

Splitter = Annotated[Union[Holdout, KFold, TimeSeriesHoldout, TimeSeriesBacktest], Field(discriminator="method")]

__all__ = ["Holdout", "KFold", "Splitter", "TimeSeriesHoldout", "TimeSeriesBacktest"]

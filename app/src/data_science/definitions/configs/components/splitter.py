from pydantic import BaseModel

from src.data_science.ds_core.definitions.splitters import Splitter


class SplitterConfig(BaseModel):
    holdout: Splitter
    backtest: Splitter

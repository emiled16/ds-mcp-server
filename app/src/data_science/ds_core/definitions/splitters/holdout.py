from typing import Literal

import numpy as np
import pandas as pd
from pydantic import ConfigDict, Field

from src.data_science.ds_core.definitions.splitters.base import BaseSplitter


class Holdout(BaseSplitter):
    method: Literal["holdout"] = Field(default="holdout")
    test_size: float = Field(default=0.2)
    shuffle: bool = Field(default=True)
    model_config = ConfigDict(extra="forbid")

    def split(self, dataset: pd.DataFrame):
        """
        Split the dataset into training and testing sets.
        Returns a generator of indexes:
        - local : return a generator of tuples (train_idx, test_idx)
        """
        if self.shuffle:
            # shuffle local dataframe
            dataset = dataset.sample(frac=1).reset_index(drop=True)
        train_idx, test_idx = np.split(dataset.index, [int(len(dataset) * (1 - self.test_size))])
        yield train_idx, test_idx

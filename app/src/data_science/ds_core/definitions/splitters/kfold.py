from typing import Literal

import numpy as np
import pandas as pd
from pydantic import ConfigDict, Field

from src.data_science.ds_core.definitions.splitters.base import BaseSplitter


class KFold(BaseSplitter):
    method: Literal["kfold"] = Field(default="kfold")
    n_splits: int = Field(default=5)
    shuffle: bool = Field(default=True)
    model_config = ConfigDict(extra="forbid")

    def split(self, dataset: pd.DataFrame):
        """
        Split the dataset into k folds.
        Returns a generator of indexes:
        - local : return a generator of tuples (train_idx, test_idx)
        - snowpark : return a generator of .where() clauses
        """
        assert isinstance(dataset, pd.DataFrame), "Dataset must be a local DataFrame"
        indices = np.arange(len(dataset))
        if self.shuffle:
            np.random.shuffle(indices)

        fold_sizes = np.full(self.n_splits, len(dataset) // self.n_splits, dtype=int)
        fold_sizes[: len(dataset) % self.n_splits] += 1
        current = 0

        for fold_size in fold_sizes:
            start, stop = current, current + fold_size
            test_idx = indices[start:stop]
            train_idx = np.concatenate([indices[:start], indices[stop:]])
            yield train_idx, test_idx
            current = stop

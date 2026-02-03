from typing import Union

import pandas as pd
from src.data_science.compat import SnowparkDataFrame

from src.data_science.ds_core.definitions.orchestration.base_pipeline import BasePipeline


class Pipeline(BasePipeline):
    def fit(self, in_memory: bool = True, **inputs: Union[pd.DataFrame, SnowparkDataFrame]) -> "Pipeline":
        self._execute("fit_transform", in_memory, **inputs)
        return self

    def transform(
        self,
        in_memory: bool = True,
        **inputs: Union[pd.DataFrame, SnowparkDataFrame],
    ) -> Union[pd.DataFrame, SnowparkDataFrame]:
        return self._execute("transform", in_memory, **inputs)

    def fit_transform(
        self,
        in_memory: bool = True,
        **inputs: Union[pd.DataFrame, SnowparkDataFrame],
    ) -> Union[pd.DataFrame, SnowparkDataFrame]:
        return self._execute("fit_transform", in_memory, **inputs)

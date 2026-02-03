from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.ds_core.atomic_functions.pandas.sort import sort as pandas_sort
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class SortParameters(BaseParameter):
    columns: list[str] = Field(default=[])
    ascending: bool = Field(default=True)


class Sort(BaseTransformation):
    name: Literal["Sort"] = "Sort"
    display_name: str = "Sort Rows"
    description: str = "Sort the dataframe by the columns specified in `columns` in ascending or descending order."
    parameters: SortParameters

    def _fit_pandas(self, df: pd.DataFrame) -> "Sort":
        return self

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return pandas_sort(df, self.parameters.columns, self.parameters.ascending)

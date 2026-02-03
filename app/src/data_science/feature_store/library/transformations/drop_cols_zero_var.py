from typing import Literal

import pandas as pd

from src.data_science.compat import SnowparkDataFrame
from src.data_science.ds_core.atomic_functions.pandas.drop_cols_zero_var import (
    drop_cols_zero_var as drop_cols_zero_var_pandas,
)
from src.data_science.ds_core.definitions.orchestration.transformation import BaseTransformation


class DropColsZeroVar(BaseTransformation):
    name: Literal["DropColsZeroVar"] = "DropColsZeroVar"
    display_name: str = "Drop Constant Columns"
    description: str = "Drop columns with zero variance from a dataframe"

    def _fit(self, _df: pd.DataFrame | SnowparkDataFrame) -> "DropColsZeroVar":
        return self

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "DropColsZeroVar":
        return self._fit(df)

    def _fit_pandas(self, df: pd.DataFrame) -> "DropColsZeroVar":
        return self._fit(df)

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return drop_cols_zero_var_pandas(df)

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        pass

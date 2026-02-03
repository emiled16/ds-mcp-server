from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.ds_core.atomic_functions.pandas.select_cols import select_cols as select_cols_pandas
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class SelectColsParameters(BaseParameter):
    columns: list[str] = Field(
        description="Columns to select from the dataframe",
        default_factory=list,
    )


class SelectCols(BaseTransformation):
    name: Literal["SelectCols"] = "SelectCols"
    display_name: str = "Select Columns"
    description: str = "Select columns from a dataframe"
    parameters: SelectColsParameters = Field(default=SelectColsParameters())

    def _fit(self, _df: pd.DataFrame) -> "SelectCols":
        return self

    def _fit_pandas(self, df: pd.DataFrame) -> "SelectCols":
        return self._fit(df)

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return select_cols_pandas(df, self.parameters.columns)

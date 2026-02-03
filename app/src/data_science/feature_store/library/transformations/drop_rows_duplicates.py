from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.compat import SnowparkDataFrame
from src.data_science.ds_core.atomic_functions.pandas.drop_rows_duplicates import (
    drop_rows_duplicates as drop_rows_duplicates_pandas,
)
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class DropRowsDuplicatesParameters(BaseParameter):
    """
    Parameters for dropping duplicate rows from a dataframe.
    """

    columns: list[str] = Field(
        description="Columns to check for duplicates",
        default_factory=list,
    )
    keep: Literal["first", "last", False] = Field(
        description="Which duplicates to keep. 'first' keeps first occurrence, 'last' keeps last occurrence, False drops all duplicates",
        default="first",
    )


class DropRowsDuplicates(BaseTransformation):
    name: Literal["DropRowsDuplicates"] = "DropRowsDuplicates"
    display_name: str = "Drop Duplicate Rows"
    description: str = "Drop duplicate rows from a dataframe based on specified columns"
    parameters: DropRowsDuplicatesParameters

    def _fit(self, _df: pd.DataFrame | SnowparkDataFrame) -> "DropRowsDuplicates":
        return self

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "DropRowsDuplicates":
        return self._fit(df)

    def _fit_pandas(self, df: pd.DataFrame) -> "DropRowsDuplicates":
        return self._fit(df)

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return drop_rows_duplicates_pandas(
            df,
            self.parameters.columns,
            self.parameters.keep,
        )

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        pass

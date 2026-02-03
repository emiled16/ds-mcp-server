from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.ds_core.atomic_functions.pandas.drop_rows_na import drop_rows_na as drop_rows_na_pandas
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class DropRowsNAParameters(BaseParameter):
    """
    Parameters for dropping rows with NA values from a dataframe.
    """

    columns: list[str] = Field(
        description="Columns to check for NA values",
        default_factory=list,
    )
    how: Literal["any", "all"] = Field(
        description="Method to drop rows. If 'any', drop a row if any specified columns contains NA. If 'all', drop only if all specified columns contain NA",
        default="any",
    )


class DropRowsNA(BaseTransformation):
    name: Literal["DropRowsNA"] = "DropRowsNA"
    display_name: str = "Drop Rows with NA Values"
    description: str = "Drop rows with NA values from a dataframe based on specified columns"
    parameters: DropRowsNAParameters

    def _fit(self, _df: pd.DataFrame) -> "DropRowsNA":
        return self

    def _fit_pandas(self, df: pd.DataFrame) -> "DropRowsNA":
        return self._fit(df)

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return drop_rows_na_pandas(
            df,
            self.parameters.columns,
            self.parameters.how,
        )

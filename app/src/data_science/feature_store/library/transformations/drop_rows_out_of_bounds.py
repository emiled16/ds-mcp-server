from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.compat import SnowparkDataFrame
from src.data_science.ds_core.atomic_functions.pandas.drop_outliers import (
    drop_rows_out_of_bounds as drop_rows_out_of_bounds_pandas,
)
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class DropRowsOutOfBoundsParameters(BaseParameter):
    """
    Parameters for dropping rows with values outside specified bounds.
    """

    column: str = Field(
        description="Column to check for out of bounds values",
    )
    lower_bound: float = Field(
        description="Lower bound value - rows with values below this will be dropped",
    )
    upper_bound: float = Field(
        description="Upper bound value - rows with values above this will be dropped",
    )


class DropRowsOutOfBounds(BaseTransformation):
    name: Literal["DropRowsOutOfBounds"] = "DropRowsOutOfBounds"
    display_name: str = "Drop Rows Out of Bounds"
    description: str = "Drop rows containing values outside specified bounds from a dataframe"
    parameters: DropRowsOutOfBoundsParameters

    def _fit(self, _df: pd.DataFrame | SnowparkDataFrame) -> "DropRowsOutOfBounds":
        return self

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "DropRowsOutOfBounds":
        return self._fit(df)

    def _fit_pandas(self, df: pd.DataFrame) -> "DropRowsOutOfBounds":
        return self._fit(df)

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return drop_rows_out_of_bounds_pandas(
            df,
            self.parameters.column,
            self.parameters.lower_bound,
            self.parameters.upper_bound,
        )

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        pass

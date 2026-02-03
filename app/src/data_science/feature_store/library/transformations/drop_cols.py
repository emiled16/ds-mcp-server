from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.compat import SnowparkDataFrame
from src.data_science.ds_core.atomic_functions.pandas.drop_cols import drop_cols as drop_cols_pandas
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class DropColsParameters(BaseParameter):
    """
    Parameters for dropping columns from a dataframe.

    Replicates same behavior as pandas, for instance:
    - df.drop(columns=['col1', 'col2'])
    """

    columns: list[str] = Field(
        description="Columns to drop from the dataframe",
        default_factory=list,
    )


class DropCols(BaseTransformation):
    name: Literal["DropCols"] = "DropCols"
    display_name: str = "Drop Columns"
    description: str = "Drop columns from a dataframe"
    parameters: DropColsParameters

    def _fit(self, _df: pd.DataFrame | SnowparkDataFrame) -> "DropCols":
        return self

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "DropCols":
        return self._fit(df)

    def _fit_pandas(self, df: pd.DataFrame) -> "DropCols":
        return self._fit(df)

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return drop_cols_pandas(df, self.parameters.columns)

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        pass

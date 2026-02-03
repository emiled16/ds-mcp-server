from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.compat import SnowparkDataFrame
from src.data_science.ds_core.atomic_functions.pandas.flatten_dict import flatten_dict as pandas_flatten_dict
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class FlattenDictParameters(BaseParameter):
    column: str = Field(
        description="Column containing dictionaries to flatten",
        default="",
    )
    drop_raw_col: bool = Field(
        description="Whether to drop the original column after flattening",
        default=False,
    )


class FlattenDict(BaseTransformation):
    name: Literal["FlattenDict"] = "FlattenDict"
    display_name: str = "Flatten Dictionary"
    description: str = """
        Flatten a column containing dictionaries into separate columns.
        Each key in the dictionary becomes a new column with prefix {column}_.
        If drop_raw_col is True, the original column is dropped.
    """
    parameters: FlattenDictParameters

    def _validate(self, df: pd.DataFrame) -> "FlattenDict":
        if self.parameters.column not in df.columns:
            raise ValueError(f"Column {self.parameters.column} not found in dataframe")
        return self

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "FlattenDict":
        return self

    def _fit_pandas(self, df: pd.DataFrame) -> "FlattenDict":
        self._validate(df)
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        pass

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        self._validate(df)
        if not self.is_fitted:
            raise ValueError("Transformation is not fitted")

        return pandas_flatten_dict(df=df, column=self.parameters.column, drop_raw_col=self.parameters.drop_raw_col)

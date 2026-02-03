from typing import Literal

import pandas as pd
from pydantic import Field
from src.data_science.compat import SnowparkDataFrame

from src.data_science.ds_core.atomic_functions.pandas.cast_types import cast_types as pandas_cast_types
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class CastTypesParameters(BaseParameter):
    columns: list[str] = Field(default=[])
    new_type: Literal["int", "float", "str", "datetime", "category"] = Field(default="int")


class CastTypes(BaseTransformation):
    name: Literal["CastTypes"] = "CastTypes"
    display_name: str = "Cast Columns Type"
    description: str = "Cast the types of the columns of the dataframe"
    parameters: CastTypesParameters

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "CastTypes":
        return self

    def _fit_pandas(self, df: pd.DataFrame) -> "CastTypes":
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        pass

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return pandas_cast_types(df, self.parameters.columns, self.parameters.new_type)

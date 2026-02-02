from typing import Literal, Union

import pandas as pd
from pydantic import Field
from snowflake.snowpark import DataFrame as SnowparkDataFrame

from src.data_science.ds_core.atomic_functions.pandas.truncate_date import truncate_date as truncate_date_pandas
from src.data_science.ds_core.atomic_functions.snowpark.truncate_date import truncate_date as truncate_date_snowpark
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class TruncDateParameters(BaseParameter):
    column: str = Field(
        description="Column to truncate",
        default="date",
    )
    unit: Literal["year", "month", "day", "hour", "minute", "second"] = Field(
        description="Unit of time to truncate the column to",
        default="month",
    )


class TruncDate(BaseTransformation):
    name: Literal["TruncDate"] = "TruncDate"
    display_name: str = "Truncate Date"
    description: str = "Truncate a dataframe's column to a given unit of time"
    parameters: TruncDateParameters

    def _fit(self, _df: Union[pd.DataFrame, SnowparkDataFrame]) -> "TruncDate":
        return self

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "TruncDate":
        return self._fit(df)

    def _fit_pandas(self, df: pd.DataFrame) -> "TruncDate":
        return self._fit(df)

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return truncate_date_pandas(df, self.parameters.column, self.parameters.unit)

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        return truncate_date_snowpark(df, self.parameters.column, self.parameters.unit)

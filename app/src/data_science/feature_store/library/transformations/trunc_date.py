from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.ds_core.atomic_functions.pandas.truncate_date import truncate_date as truncate_date_pandas
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

    def _fit(self, _df: pd.DataFrame) -> "TruncDate":
        return self

    def _fit_pandas(self, df: pd.DataFrame) -> "TruncDate":
        return self._fit(df)

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return truncate_date_pandas(df, self.parameters.column, self.parameters.unit)

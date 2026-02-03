from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class TimeSeriesRecencyParameters(BaseParameter):
    datetime_column: str = Field(default="", description="Column to transform")
    dimension_columns: list[str] = Field(default=[], description="Columns to group by")
    output_column: str = Field(default="time_series_recency", description="Output column name")
    target_column: str = Field(default="", description="Column to transform")


class TimeSeriesRecency(BaseTransformation):
    name: Literal["TimeSeriesRecency"] = "TimeSeriesRecency"
    display_name: str = "Time Series Recency"
    description: str = """
        Add the time series recency to the dataframe.
        The time series recency is the number of days since the last observation by dimension.
    """
    parameters: TimeSeriesRecencyParameters = TimeSeriesRecencyParameters()

    def _fit_pandas(self, df: pd.DataFrame) -> "TimeSeriesRecency":
        if any(dim not in df.columns for dim in self.parameters.dimension_columns):
            raise ValueError("Dimension columns not found in dataframe")
        if self.parameters.datetime_column not in df.columns:
            raise ValueError("Datetime column not found in dataframe")
        return self

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_values(by=[*self.parameters.dimension_columns, self.parameters.datetime_column])
        df = df.assign(dummy=lambda x: x[self.parameters.target_column] != 0)
        df_tmp = df.groupby(self.parameters.dimension_columns).agg({"dummy": "cumsum"})
        df = df.drop(columns=["dummy"]).merge(df_tmp, left_index=True, right_index=True, how="left")
        df[self.parameters.output_column] = (
            df.groupby([*self.parameters.dimension_columns, "dummy"]).cumcount().shift().fillna(0)
        )
        return df.drop(
            columns=["dummy"],
        )

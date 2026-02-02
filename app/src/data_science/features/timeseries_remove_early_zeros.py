from typing import Literal

import pandas as pd
from pydantic import Field
from snowflake.snowpark import DataFrame as SnowparkDataFrame

from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class TimeSeriesRemoveEarlyZerosParameters(BaseParameter):
    datetime_column: str = Field(default="", description="Column to transform")
    dimension_columns: list[str] = Field(default=[], description="Columns to group by")
    metric_column: str = Field(default="", description="Column Name")


class TimeSeriesRemoveEarlyZeros(BaseTransformation):
    name: Literal["TimeSeriesRemoveEarlyZeros"] = "TimeSeriesRemoveEarlyZeros"
    display_name: str = "Time Series Recency"
    description: str = """
        Add the time series recency to the dataframe.
        The time series recency is the number of days since the last observation by dimension.
    """
    parameters: TimeSeriesRemoveEarlyZerosParameters = TimeSeriesRemoveEarlyZerosParameters()

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "TimeSeriesRemoveEarlyZeros":
        raise NotImplementedError("TimeSeriesRemoveEarlyZeros is not implemented for snowpark")

    def _fit_pandas(self, df: pd.DataFrame) -> "TimeSeriesRemoveEarlyZeros":
        if any(dim not in df.columns for dim in self.parameters.dimension_columns):
            raise ValueError("Dimension columns not found in dataframe")
        if self.parameters.datetime_column not in df.columns:
            raise ValueError("Datetime column not found in dataframe")
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        raise NotImplementedError("TimeSeriesRemoveEarlyZeros is not implemented for snowpark")

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_index()
        df_indexes = list(df.index.names)
        df = df.reset_index()
        df_filtered = df[lambda _d: _d[self.parameters.metric_column != 0]]
        df_grouped = (
            df_filtered.groupby(self.parameters.dimension_columns)
            if len(self.parameters.dimension_columns) > 0
            else df_filtered
        )
        min_dates_df = (
            df_grouped.agg({self.parameters.datetime_column: "min"})
            .reset_index()
            .rename(columns={self.parameters.datetime_column: "min_date"})
        )
        df = df.merge(
            min_dates_df, on=self.parameters.dimension_columns
        )  # TODO: manage the case when the dimension_columns is empty
        df = df[lambda _d: _d[self.parameters.datetime_column] >= _d["min_date"]].set_index(df_indexes)
        return df

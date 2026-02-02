from typing import Literal

import pandas as pd
from pydantic import Field
from snowflake.snowpark import DataFrame as SnowparkDataFrame

from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class TimeSeriesFrequencyParameters(BaseParameter):
    datetime_column: str = Field(default="", description="Column to transform")
    dimension_columns: list[str] = Field(default=[], description="Columns to group by")
    output_column: str = Field(default="time_series_frequency", description="Output column name")
    target_column: str = Field(default="", description="Column where metric is")


class TimeSeriesFrequency(BaseTransformation):
    name: Literal["TimeSeriesFrequency"] = "TimeSeriesFrequency"
    display_name: str = "Time Series Frequency"
    description: str = """
        Add the time series frequency to the dataframe.
        The time series frequency is the number of observations by dimension.
    """
    parameters: TimeSeriesFrequencyParameters = TimeSeriesFrequencyParameters()

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "TimeSeriesFrequency":
        raise NotImplementedError("TimeSeriesFrequency is not implemented for snowpark")

    def _fit_pandas(self, df: pd.DataFrame) -> "TimeSeriesFrequency":
        if any(dim not in df.columns for dim in self.parameters.dimension_columns):
            raise ValueError(f"Dimension columns {self.parameters.dimension_columns} not found in dataframe")
        if self.parameters.datetime_column not in df.columns:
            raise ValueError(f"Datetime column {self.parameters.datetime_column} not found in dataframe")
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        raise NotImplementedError("TimeSeriesFrequency is not implemented for snowpark")

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_index()
        df_indexes = list(df.index.names)
        df_grouped = df.groupby(self.parameters.dimension_columns) if len(self.parameters.dimension_columns) > 0 else df
        return df.merge(
            df_grouped.apply(lambda ds: (ds[self.parameters.target_column] != 0).expanding().sum().shift().fillna(0))
            .rename(self.parameters.output_column)
            .reset_index()[[*df_indexes, self.parameters.output_column]]
            .set_index(df_indexes),
            left_index=True,
            right_index=True,
        )

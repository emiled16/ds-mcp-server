from typing import Literal

import pandas as pd
from pydantic import Field
from src.data_science.compat import SnowparkDataFrame

from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class TimeSeriesAgeParameters(BaseParameter):
    datetime_column: str = Field(default="", description="Column to transform")
    dimension_columns: list[str] = Field(default=[], description="Columns to group by")
    output_column: str = Field(default="time_series_age", description="Output column name")


class TimeSeriesAge(BaseTransformation):
    name: Literal["TimeSeriesAge"] = "TimeSeriesAge"
    display_name: str = "Time Series Age"
    description: str = """
        Add the time series age to the dataframe.
        The time series age is the number of days since the first observation by dimension.
    """
    parameters: TimeSeriesAgeParameters = TimeSeriesAgeParameters()

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "TimeSeriesAge":
        raise NotImplementedError("TimeSeriesAge is not implemented for snowpark")

    def _fit_pandas(self, df: pd.DataFrame) -> "TimeSeriesAge":
        if any(dim not in df.columns for dim in self.parameters.dimension_columns):
            raise ValueError(f"Dimension columns {self.parameters.dimension_columns} not found in dataframe")
        if self.parameters.datetime_column not in df.columns:
            raise ValueError(f"Datetime column {self.parameters.datetime_column} not found in dataframe")
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        raise NotImplementedError("TimeSeriesAge is not implemented for snowpark")

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.assign(**{self.parameters.output_column: 1})

        df_tmp = (
            df.sort_values(by=[*self.parameters.dimension_columns, self.parameters.datetime_column]).groupby(
                self.parameters.dimension_columns,
            )
            if self.parameters.dimension_columns
            else df
        )

        df = df.drop(columns=[self.parameters.output_column])
        df_tmp = df_tmp[[self.parameters.output_column]].cumsum().astype(int)
        return df.merge(df_tmp, left_index=True, right_index=True, how="left")

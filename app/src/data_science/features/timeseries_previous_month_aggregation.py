from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.compat import SnowparkDataFrame
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class PreviousMonthAggregationParameters(BaseParameter):
    window_sizes: list[int] = Field(default=[1], description="Lags to use")
    target_column: str = Field(default="", description="Target column to calculate the aggregation and lag")
    target_column_transformations: list[
        Literal["mean", "sum", "min", "max", "std", "var", "count", "first", "last"]
    ] = Field(
        default=["mean"],
        description="Transformation to apply to the target column",
    )
    suffix: str = Field(default="", description="Suffix to add to the rolling features")
    partition_columns: list[str] = Field(default=[], description="Partition columns to calculate the aggregation on")
    order_by_columns: list[str] = Field(default=[], description="Order by columns to calculate the aggregation on")
    month_column: str = Field(default="month")
    year_column: str = Field(default="year")
    fillna: bool = Field(default=True, description="Fill NANs with 0s")


class PreviousMonthAggregation(BaseTransformation):
    name: Literal["PreviousMonthAggregation"] = "PreviousMonthAggregation"
    display_name: str = "Previous Month Aggregation"
    description: str = """
        Aggregate a colum by month and the lags it
        example:
            previous total transaction amount
    """
    parameters: PreviousMonthAggregationParameters = PreviousMonthAggregationParameters()

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "PreviousMonthAggregation":
        return self

    def _fit_pandas(self, df: pd.DataFrame) -> "PreviousMonthAggregation":
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        raise NotImplementedError("PreviousMonthAggregation is not implemented for snowpark")

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        indexes = df.index.names
        df = df.reset_index()
        for window in self.parameters.window_sizes:
            for transformation in self.parameters.target_column_transformations:
                name = f"average_previous_{window}_{transformation}_month_{self.parameters.target_column}"
                ds = (
                    df.groupby(
                        [*self.parameters.partition_columns, self.parameters.year_column, self.parameters.month_column]
                    )
                    .agg({self.parameters.target_column: transformation})
                    .rename(columns={self.parameters.target_column: name})
                    .reset_index()
                    .groupby(self.parameters.partition_columns)
                    .apply(
                        lambda _d: _d.sort_values([self.parameters.year_column, self.parameters.month_column])
                        .set_index([self.parameters.year_column, self.parameters.month_column])[name]
                        .rolling(window=window, closed="left")
                        .agg({name: "mean"}),
                    )
                    .reset_index()
                )
                if self.parameters.fillna:
                    ds[name] = ds[name].fillna(0)

                df = df.merge(
                    ds,
                    on=[*self.parameters.partition_columns, self.parameters.year_column, self.parameters.month_column],
                )

        return df.set_index(indexes)

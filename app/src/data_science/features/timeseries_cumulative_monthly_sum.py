from typing import Literal

import pandas as pd
from pydantic import Field
from src.data_science.compat import SnowparkDataFrame

from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class CumulativeMonthlySumParameters(BaseParameter):
    target_column: str = Field(default="", description="Target column to calculate the aggregation and lag")
    suffix: str = Field(default="", description="Suffix to add to the rolling features")
    partition_columns: list[str] = Field(default=[], description="Partition columns to calculate the aggregation on")
    order_by_columns: list[str] = Field(default=[], description="Order by columns to calculate the aggregation on")
    month_column: str = Field(default="month")
    year_column: str = Field(default="year")
    fillna: bool = Field(default=True, description="Fill NANs with 0s")


class CumulativeMonthlySum(BaseTransformation):
    name: Literal["CumulativeMonthlySum"] = "CumulativeMonthlySum"
    display_name: str = "Cumulative Monthly Sum"
    description: str = """
        Compute the Cumulative monthly sum for a target column
    """
    parameters: CumulativeMonthlySumParameters = CumulativeMonthlySumParameters()

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "CumulativeMonthlySum":
        return self

    def _fit_pandas(self, df: pd.DataFrame) -> "CumulativeMonthlySum":
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        raise NotImplementedError("CumulativeMonthlySum is not implemented for snowpark")

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        indexes = df.index.names

        new_df = (
            df.reset_index()
            .merge(
                df.reset_index()
                .groupby(
                    [*self.parameters.partition_columns, self.parameters.year_column, self.parameters.month_column]
                )
                .apply(
                    lambda _d: _d.sort_values(self.parameters.order_by_columns)
                    .set_index(self.parameters.order_by_columns)[self.parameters.target_column]
                    .cumsum()
                    .shift()
                    .fillna(0)
                )
                .reset_index()
                .rename(
                    columns={self.parameters.target_column: f"cumulative_monthly_sum_{self.parameters.target_column}"}
                ),
                on=[
                    *self.parameters.partition_columns,
                    *self.parameters.order_by_columns,
                    self.parameters.year_column,
                    self.parameters.month_column,
                ],
            )
            .set_index(indexes)
        )

        return new_df

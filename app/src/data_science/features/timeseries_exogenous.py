from typing import Literal

import pandas as pd
from pydantic import Field
from snowflake.snowpark import DataFrame as SnowparkDataFrame

from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation
from src.data_science.utils.snowflake import snowpark_session


class TimeSeriesExogenousParameters(BaseParameter):
    database_name: str = Field(default="MAXA_SNBX")
    schema_name: str = Field(default="DATA_MART")
    table_name: str = Field(default="MART_EOM_TIME_SERIES_BY_COUNTERPARTY_DIRECTION")

    join_columns: list[str] = Field(
        default=["direction", "counterparty_id"],
        description="Columns to use for join",
    )
    exogenous_columns: list[str] = Field(default=[], description="Columns to add")


class TimeSeriesExogenous(BaseTransformation):
    name: Literal["TimeSeriesExogenous"] = "TimeSeriesExogenous"
    display_name: str = "Time Series Exogenous (Snowflake)"
    description: str = """
        Add Dimensional Exogenous Data from Snowflake Table
    """
    parameters: TimeSeriesExogenousParameters = TimeSeriesExogenousParameters()

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "TimeSeriesExogenousParameters":
        raise NotImplementedError("TimeSeriesExogenous is not implemented for snowpark")

    def _fit_pandas(self, df: pd.DataFrame) -> "TimeSeriesExogenousParameters":
        if any(dim not in df.columns for dim in self.parameters.join_columns):
            raise ValueError(f"Dimension columns {self.parameters.join_columns} not found in dataframe")
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        raise NotImplementedError("TimeSeriesExogenous is not implemented for snowpark")

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        session = snowpark_session()

        table_fqn = f"{self.parameters.database_name}.{self.parameters.schema_name}.{self.parameters.table_name}"

        exogenous_df = (
            session.table(table_fqn)
            .to_pandas()
            .rename(columns=str.lower)[[*self.parameters.join_columns, *self.parameters.exogenous_columns, "date"]]
        )
        if "date" in exogenous_df.columns:
            exogenous_df["date"] = pd.to_datetime(exogenous_df["date"])

        exogenous_df["forecast_month"] = exogenous_df["date"].apply(lambda x: x.replace(day=1).strftime("%Y-%m-%d"))
        df["forecast_month"] = df["date"].apply(lambda x: x.replace(day=1).strftime("%Y-%m-%d"))
        exogenous_df = exogenous_df[
            ["forecast_month", *self.parameters.join_columns, *self.parameters.exogenous_columns]
        ].drop_duplicates()

        indexes = df.index.names
        df = df.reset_index()

        df = df.merge(exogenous_df, on=["forecast_month", *self.parameters.join_columns], how="left")
        df = df.drop(columns=["forecast_month"])

        df = df.set_index(indexes)

        return df

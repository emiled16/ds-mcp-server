from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation
from src.data_science.snowflake_optional import F, require_snowflake
from src.data_science.utils.snowflake import snowpark_session


class TimeSeriesSegmentationFilteringParameters(BaseParameter):
    database_name: str = Field(default="MAXA_SNBX")
    schema_name: str = Field(default="DATA_MART")
    table_name: str = Field(default="MART_EOM_TIME_SERIES_BY_COUNTERPARTY_DIRECTION")

    dim_value_name: str = Field(default="dim_value", description="Name of the counterparty id column")
    date_column_name: str = Field(default="date", description="Name of the date column")
    segment_col: str = Field(default="eom_pattern_primary")
    segments_to_keep: list[str] = Field(
        default=[
            "continuous_volatile",
            "continuous_stable",
            "rare_recent",
            "intermittent_active",
        ],
        description="List of segments to keep, others will be filtered out",
    )


class TimeSeriesSegmemtationFiltering(BaseTransformation):
    name: Literal["TimeSeriesSegmemtationFiltering"] = "TimeSeriesSegmemtationFiltering"
    display_name: str = "Time Series Segmentation Filtering"
    description: str = """
        Filter the feature store based on segmentation through a temporal join
    """
    parameters: TimeSeriesSegmentationFilteringParameters = TimeSeriesSegmentationFilteringParameters()

    def _fit_pandas(self, df: pd.DataFrame) -> "TimeSeriesSegmemtationFiltering":
        return self

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        require_snowflake()
        session = snowpark_session()

        table_fqn = f"{self.parameters.database_name}.{self.parameters.schema_name}.{self.parameters.table_name}"

        exogenous_df = (
            (
                session.table(table_fqn)
                .filter(F.col(self.parameters.segment_col).isin(self.parameters.segments_to_keep))
                .to_pandas()
                .rename(columns=str.lower)
            )[
                [
                    self.parameters.dim_value_name,
                    self.parameters.date_column_name,
                    self.parameters.segment_col,
                ]
            ]
            .assign(
                counterparty_id=lambda _d: _d[self.parameters.dim_value_name].apply(lambda x: x.split("::")[0]),
                direction=lambda _d: _d[self.parameters.dim_value_name].apply(lambda x: x.split("::")[1]),
            )
            .drop_duplicates()
        )

        indexes = df.index.names
        df = df.reset_index()
        exogenous_df[self.parameters.date_column_name] = pd.to_datetime(exogenous_df[self.parameters.date_column_name])

        exogenous_df["forecast_month"] = exogenous_df["date"].apply(lambda x: x.replace(day=1).strftime("%Y-%m-%d"))
        df["forecast_month"] = df["date"].apply(lambda x: x.replace(day=1).strftime("%Y-%m-%d"))

        exogenous_df = exogenous_df[
            ["counterparty_id", "direction", "forecast_month", self.parameters.segment_col]
        ].drop_duplicates()
        df = exogenous_df.merge(df, on=["counterparty_id", "direction", "forecast_month"], how="inner")

        df = df.drop(columns=["forecast_month"])

        df = df.set_index(indexes)

        return df

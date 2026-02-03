from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation
from src.data_science.utils.snowflake import snowpark_session


class TimeSeriesDimCalendarParameters(BaseParameter):
    database_name: str = Field(default="MAXA_SNBX")
    schema_name: str = Field(default="DATA_MART")
    table_name: str = Field(default="DIM_CALENDAR")


class TimeSeriesDimCalendar(BaseTransformation):
    name: Literal["TimeSeriesDimCalendar"] = "TimeSeriesDimCalendar"
    display_name: str = "Time Series Dim Calendar"
    description: str = "Add Calemdar Feaure from dim calendar"
    parameters: TimeSeriesDimCalendarParameters = TimeSeriesDimCalendarParameters()

    def _fit_pandas(self, df: pd.DataFrame) -> "TimeSeriesDimCalendarParameters":
        return self

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        session = snowpark_session()

        table_fqn = f"{self.parameters.database_name}.{self.parameters.schema_name}.{self.parameters.table_name}"

        exogenous_df = session.table(table_fqn).to_pandas()

        exogenous_df = exogenous_df.rename(columns=str.lower)[
            [
                "date_day",
                "month_of_year",
                "year_number",
                "week_of_year",
                "quarter_of_year",
                "day_of_week_ds",
                "day_of_month",
                "day_of_year",
                "is_weekend",
                "is_holiday",
                "is_work_day",
                "row_number_work_day_of_month",
                "row_number_work_day_of_month_desc",
                "row_number_work_day_of_quarter",
                "row_number_work_day_of_quarter_desc",
                "is_first_work_day_of_month",
                "is_last_work_day_of_month",
                "is_mid_work_day_of_month",
                "is_first_work_day_of_quarter",
                "is_last_work_day_of_quarter",
                # already named correctly
                "sin_month",
                "cos_month",
                "sin_week",
                "cos_week",
                "sin_day_of_week",
                "cos_day_of_week",
                "sin_day_of_month",
                "cos_day_of_month",
                "sin_day_of_year",
                "cos_day_of_year",
                "distance_since_previous_is_holiday",
                "distance_until_next_is_holiday",
                "distance_since_previous_is_weekend",
                "distance_until_next_is_weekend",
                "distance_since_previous_is_mid_work_day_of_month",
                "distance_until_next_is_mid_work_day_of_month",
                "distance_since_previous_is_first_work_day_of_month",
                "distance_until_next_is_first_work_day_of_month",
                "distance_since_previous_is_last_work_day_of_month",
                "distance_until_next_is_last_work_day_of_month",
                "distance_since_previous_is_first_work_day_of_quarter",
                "distance_until_next_is_first_work_day_of_quarter",
            ]
        ].rename(
            columns={
                "day_of_week_ds": "day_of_week",
                "date_day": "date",
                "month_of_year": "month",
                "year_number": "year",
                "week_of_year": "week",
                "quarter_of_year": "quarter",
                "is_work_day": "is_workday",
                "row_number_work_day_of_month": "workday_of_month",
                "row_number_work_day_of_month_desc": "workday_of_month_reverse",
                "row_number_work_day_of_quarter": "workday_of_quarter",
                "row_number_work_day_of_quarter_desc": "workday_of_quarter_reverse",
                "is_first_work_day_of_month": "is_first_workday_of_month",
                "is_last_work_day_of_month": "is_last_workday_of_month",
                "is_mid_work_day_of_month": "is_mid_month",
                "is_first_work_day_of_quarter": "is_first_workday_of_quarter",
                "is_last_work_day_of_quarter": "is_last_workday_of_quarter",
            }
        )
        exogenous_df["date"] = pd.to_datetime(exogenous_df["date"])

        indexes = df.index.names
        df = df.reset_index()

        df = df.merge(exogenous_df, on=["date"], how="left")

        df = df.set_index(indexes)

        return df

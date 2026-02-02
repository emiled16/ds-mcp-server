import calendar
from typing import Literal

import holidays
import numpy as np
import pandas as pd
from loguru import logger
from pydantic import Field
from snowflake.snowpark import DataFrame as SnowparkDataFrame
from snowflake.snowpark.context import get_active_session

from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation

# - Standard time series features:
#   - [ ] day of the week
#   - [ ] day of the month
#   - [ ] day of the year
#   - [ ] workday of the month
#   - [ ] month
#   - [ ] year
#   - [ ] week
#   - [ ] workday
#   - [ ] is_weekend
#   - [ ] is_holiday
#   - [ ] is_first_day_of_month
#   - [ ] is_last_day_of_month
#   - [ ] is_mid_month
#   - [ ] is_quarter_start
#   - [ ] is_quarter_end


def add_basic_calendar_features(
    df: pd.DataFrame,
    datetime_column: str,
    holidays_countries: list[str],
    table_name: str = "MAXA_DEV.DATA_MART.DIM_CALENDAR",
) -> pd.DataFrame:
    session = get_active_session()
    dim_calendar = (
        session.table(table_name).to_pandas().rename(columns=str.lower)[["date_day", "is_last_work_day_of_month"]]
    ).rename(columns={"date_day": "date", "is_last_work_day_of_month": "is_last_workday_of_month"})
    dim_calendar["date"] = pd.to_datetime(dim_calendar["date"])
    holidays_countries = [holidays.country_holidays(country=country) for country in holidays_countries]
    df_copy = df.copy(deep=True)
    df = df[[datetime_column]].drop_duplicates().sort_values(datetime_column, ascending=True).reset_index(drop=True)
    # convert to datetime
    df[datetime_column] = pd.to_datetime(df[datetime_column])
    # add basic calendar features
    df["month"] = df[datetime_column].dt.month
    df["year"] = df[datetime_column].dt.year
    df["week"] = df[datetime_column].dt.isocalendar().week
    df["quarter"] = df[datetime_column].dt.quarter
    df["day_of_week"] = df[datetime_column].dt.dayofweek
    df["day_of_month"] = df[datetime_column].dt.day
    df["day_of_year"] = df[datetime_column].dt.dayofyear
    ###################################
    df["is_weekend"] = df[datetime_column].apply(lambda x: x.weekday() >= 5)
    df["is_holiday"] = df[datetime_column].apply(
        lambda x: any(holiday for holiday in holidays_countries if x in holiday),
    )
    df["is_workday"] = df.apply(
        lambda _d: not _d["is_weekend"] and not _d["is_holiday"],
        axis=1,
    )

    df["workday_of_month"] = (
        df.assign(workday_of_month=1).groupby(["year", "month", "is_workday"])["workday_of_month"].cumsum()
    ).where(df["is_workday"], -1)

    df["workday_of_month_reverse"] = (
        df.groupby(["year", "month", "is_workday"])["workday_of_month"].transform("max") - df["workday_of_month"] + 1
    ).where(df["is_workday"], np.nan)

    df["is_first_workday_of_month"] = df["workday_of_month"] == 1
    df = df.merge(dim_calendar, on=["date"])

    df["is_mid_month"] = df["workday_of_month"].isin([9, 10, 11, 12])
    df["is_first_workday_of_quarter"] = df.groupby(["year", "quarter"])["is_workday"].cumsum() == 1

    list_last_workday_quarter = (
        df[df["is_last_workday_of_month"]]
        .sort_values(["year", "quarter"])
        .groupby(["year", "quarter"])
        .last()["date"]
        .to_numpy()
    )
    df["is_last_workday_of_quarter"] = False
    df.loc[df["date"].isin(list_last_workday_quarter), "is_last_workday_of_quarter"] = True

    ###################################
    # add cyclical time periods
    df["sin_month"] = df["month"].apply(lambda x: np.sin(x * 2 * np.pi / 12))
    df["cos_month"] = df["month"].apply(lambda x: np.cos(x * 2 * np.pi / 12))
    df["sin_week"] = df["week"].apply(lambda x: np.sin(x * 2 * np.pi / 52))
    df["cos_week"] = df["week"].apply(lambda x: np.cos(x * 2 * np.pi / 52))
    df["sin_day_of_week"] = df["day_of_week"].apply(lambda x: np.sin(x * 2 * np.pi / 7))
    df["cos_day_of_week"] = df["day_of_week"].apply(lambda x: np.cos(x * 2 * np.pi / 7))
    df["sin_day_of_month"] = df.apply(
        lambda _d: np.sin(_d["day_of_month"] * 2 * np.pi / calendar.monthrange(_d["year"], _d["month"])[1]),
        axis=1,
    )
    df["cos_day_of_month"] = df.apply(
        lambda _d: np.cos(_d["day_of_month"] * 2 * np.pi / calendar.monthrange(_d["year"], _d["month"])[1]),
        axis=1,
    )
    df["sin_day_of_year"] = df["day_of_year"].apply(lambda x: np.sin(x * 2 * np.pi / 365))
    df["cos_day_of_year"] = df["day_of_year"].apply(lambda x: np.cos(x * 2 * np.pi / 365))

    index_columns = df_copy.index.names
    return (
        df_copy.reset_index()
        .merge(
            df,
            on=datetime_column,
            how="left",
        )
        .set_index(index_columns)
    )


class BasicCalendarParameters(BaseParameter):
    datetime_column: str = Field(default="", description="Column to transform")
    countries: list[str] = Field(default=["Canada"], description="Countries to use for holidays")


class BasicCalendar(BaseTransformation):
    name: Literal["BasicCalendar"] = "BasicCalendar"
    display_name: str = "Basic Calendar"
    description: str = """
        Transform a datetime column into basic calendar features.
        The datetime column is first converted to a datetime object and then transformed into basic calendar features.
        The resulting dataframe will have the original datetime column plus the new basic calendar features.
    """
    parameters: BasicCalendarParameters = BasicCalendarParameters()

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "BasicCalendar":
        return self

    def _fit_pandas(self, df: pd.DataFrame) -> "BasicCalendar":
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        pass

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return add_basic_calendar_features(df, self.parameters.datetime_column, self.parameters.countries)

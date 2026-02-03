import calendar
from typing import Literal

import holidays
import numpy as np
import pandas as pd
from pydantic import Field

from src.data_science.compat import SnowparkDataFrame
from src.data_science.ds_core.definitions.orchestration.transformation import (
    BaseParameter,
    BaseTransformation,
)

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


def add_basic_calendar_features(df: pd.DataFrame, datetime_column: str, holidays_countries: list[str]) -> pd.DataFrame:
    holidays_countries = [holidays.country_holidays(country=country) for country in holidays_countries]
    df = df.copy()
    # convert to datetime
    if pd.api.types.is_period_dtype(df[datetime_column]):
        df[datetime_column] = df[datetime_column].dt.start_time
    elif df[datetime_column].apply(lambda x: isinstance(x, pd.Period)).any():
        # If any element is a Period, convert all to timestamp
        df[datetime_column] = df[datetime_column].apply(lambda x: x.to_timestamp() if isinstance(x, pd.Period) else x)
        df[datetime_column] = pd.to_datetime(df[datetime_column])
    else:
        df[datetime_column] = pd.to_datetime(df[datetime_column])
    # add basic calendar features
    df["month"] = df[datetime_column].dt.month
    df["year"] = df[datetime_column].dt.year
    df["week"] = df[datetime_column].dt.isocalendar().week.astype("int64")
    df["day_of_week"] = df[datetime_column].dt.dayofweek
    df["day_of_month"] = df[datetime_column].dt.day
    df["day_of_year"] = df[datetime_column].dt.dayofyear
    df["workday_of_month"] = df[datetime_column].apply(
        lambda x: x.day <= calendar.monthrange(x.year, x.month)[1] and x.day >= 1 and x.weekday() < 5,
    )
    df["is_weekend"] = df[datetime_column].apply(lambda x: x.weekday() >= 5)
    df["is_holiday"] = df[datetime_column].apply(
        lambda x: any(holiday for holiday in holidays_countries if x in holiday),
    )
    df["is_first_day_of_month"] = df[datetime_column].apply(lambda x: x.day == 1)
    df["is_last_day_of_month"] = df[datetime_column].apply(lambda x: x.day == calendar.monthrange(x.year, x.month)[1])
    df["is_mid_month"] = df[datetime_column].apply(lambda x: x.day > 15)
    df["is_quarter_start"] = df[datetime_column].apply(lambda x: x.month % 3 == 1)
    df["is_quarter_end"] = df[datetime_column].apply(lambda x: x.month % 3 == 0)
    # add cyclical time periods
    df["sin_month"] = df["month"].apply(lambda x: np.sin(x * 2 * np.pi / 12))
    df["cos_month"] = df["month"].apply(lambda x: np.cos(x * 2 * np.pi / 12))
    df["sin_week"] = df["week"].apply(lambda x: np.sin(x * 2 * np.pi / 52))
    df["cos_week"] = df["week"].apply(lambda x: np.cos(x * 2 * np.pi / 52))
    df["sin_day_of_week"] = df["day_of_week"].apply(lambda x: np.sin(x * 2 * np.pi / 7))
    df["cos_day_of_week"] = df["day_of_week"].apply(lambda x: np.cos(x * 2 * np.pi / 7))
    return df


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

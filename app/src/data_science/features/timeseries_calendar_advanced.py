from typing import Literal

import pandas as pd
from pydantic import Field, model_validator
from snowflake.snowpark import DataFrame as SnowparkDataFrame

from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation

#   - [ ] distance since previous holiday
#   - [ ] distance until next holiday
#   - [ ] distance since previous first work day of month
#   - [ ] distance until next first work day of month
#   - [ ] distance since previous last work day of month
#   - [ ] distance until next last work day of month
#   - [ ] distance since previous mid-month work day
#   - [ ] distance until next mid-month work day


class AdvancedCalendarParameters(BaseParameter):
    is_holiday_column: str = Field(default="is_holiday", description="Column to transform")
    is_weekend_column: str = Field(default="is_weekend", description="Column to transform")
    is_workday_column: str = Field(default="is_workday", description="Column to transform")
    is_mid_month_column: str = Field(default="is_mid_month", description="Column to transform")
    is_first_workday_of_month_column: str = Field(
        default="is_first_workday_of_month",
        description="Column to transform",
    )
    is_last_workday_of_month_column: str = Field(default="is_last_workday_of_month", description="Column to transform")
    is_first_workday_of_quarter_column: str = Field(
        default="is_first_workday_of_quarter",
        description="Column to transform",
    )
    datetime_column: str = Field(default="datetime", description="Column to transform")

    all_columns: list[str] | None = Field(default=None, description="All columns to transform")

    @model_validator(mode="after")
    def get_all_columns(self):
        if self.all_columns is None:
            self.all_columns = [
                self.is_holiday_column,
                self.is_weekend_column,
                self.is_workday_column,
                self.is_mid_month_column,
                self.is_first_workday_of_month_column,
                self.is_last_workday_of_month_column,
                self.is_first_workday_of_quarter_column,
            ]


class AdvancedCalendar(BaseTransformation):
    name: Literal["AdvancedCalendar"] = "AdvancedCalendar"
    display_name: str = "Advanced Calendar"
    description: str = """
        Transform a datetime column into advanced calendar features.
        The datetime column is first converted to a datetime object and then transformed into advanced calendar features.
        The resulting dataframe will have the original datetime column plus the new advanced calendar features.
    """
    parameters: AdvancedCalendarParameters = AdvancedCalendarParameters()

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "AdvancedCalendar":
        raise NotImplementedError("AdvancedCalendar is not implemented for snowpark")

    def _fit_pandas(self, df: pd.DataFrame) -> "AdvancedCalendar":
        if not self.parameters.all_columns:
            raise ValueError("all_columns is not set")

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        raise NotImplementedError("AdvancedCalendar is not implemented for snowpark")

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        indexes = df.index.names
        df_copy = df.copy(deep=True).reset_index()

        if not self.parameters.all_columns:
            raise ValueError("all_columns is not set")

        df = df.drop_duplicates(["date"]).set_index(["date"])

        list_features_distances: list[pd.Series] = []
        for col in self.parameters.all_columns:
            # distance since col
            s = df[[col]].cumsum().groupby(col).cumcount()
            s.name = f"distance_since_previous_{col}"
            list_features_distances.append(s)

            # distance until col
            s = df[[col]].iloc[::-1].cumsum().groupby(col).cumcount().iloc[::-1]
            s.name = f"distance_until_next_{col}"
            list_features_distances.append(s)
        df_features: pd.DataFrame = pd.concat(list_features_distances, axis=1)
        df_features = df_features.reset_index()

        return df_copy.merge(df_features, on="date", how="left").set_index(indexes)

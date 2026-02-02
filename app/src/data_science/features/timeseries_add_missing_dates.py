from typing import Literal

import pandas as pd
from pydantic import Field
from snowflake.snowpark import DataFrame as SnowparkDataFrame

from src.data_science.definitions.configs.components.timeseries import Periodicity
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation

mapping_periodicity_to_freq = {
    "daily": "D",
    "weekly": "W",
    "monthly": "M",
    "quarterly": "Q",
    "yearly": "Y",
}


class AddMissingDatesParameters(BaseParameter):
    date_column: str = Field(default="", description="Column to add missing dates")
    dimensions: list[str] = Field(default=[], description="Columns to group by")
    periodicity: Periodicity = Field(default="monthly", description="Periodicity to add missing dates")
    date_column_idx: str = Field(default="date_idx", description="Column to use as index")


class AddMissingDates(BaseTransformation):
    name: Literal["AddMissingDates"] = "AddMissingDates"
    display_name: str = "Add Missing Dates"
    description: str = """
        Add missing dates in the dataframe. (custom to BNC)
    """
    parameters: AddMissingDatesParameters = AddMissingDatesParameters()

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "AddMissingDates":
        raise NotImplementedError("AddMissingDates is not implemented for snowpark")

    def _fit_pandas(self, df: pd.DataFrame) -> "AddMissingDates":
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        raise NotImplementedError("AddMissingDates is not implemented for snowpark")

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        df_copy = df.copy(deep=True).reset_index(drop=True)
        min_date = df[self.parameters.date_column].min()
        max_date = df[self.parameters.date_column].max()
        dates = pd.date_range(
            start=min_date,
            end=max_date,
            freq=mapping_periodicity_to_freq[self.parameters.periodicity],
        )
        indexes = df.index.names
        indexes_minus_date_idx = [idx for idx in indexes if idx != self.parameters.date_column_idx]
        df = df.reset_index()

        return (
            (
                df[[*self.parameters.dimensions, *indexes_minus_date_idx]]
                .drop_duplicates()
                .join(
                    pd.DataFrame(dates, columns=[self.parameters.date_column]),
                    how="cross",
                )
                .merge(
                    df.groupby(self.parameters.dimensions)[self.parameters.date_column].min().rename("min_date"),
                    on=self.parameters.dimensions,
                    how="left",
                )[lambda _d: _d[self.parameters.date_column] >= _d["min_date"]]
                .drop(columns=["min_date"])
                .assign(
                    **{self.parameters.date_column_idx: lambda df: df[self.parameters.date_column]},
                )
            )
            .merge(
                df_copy,
                on=[*self.parameters.dimensions, self.parameters.date_column],
                how="left",
            )
            .set_index(indexes)
        )

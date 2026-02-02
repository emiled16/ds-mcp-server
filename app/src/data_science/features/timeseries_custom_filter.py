from typing import Literal

import pandas as pd
from pydantic import Field
from snowflake.snowpark import DataFrame as SnowparkDataFrame

from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class CustomFilterParameters(BaseParameter):
    workdays_to_include: list[int] = Field(
        default_factory=list,
        description="Workdays to include, if empty include all workdays",
    )
    workdays_reverse_to_include: list[int] = Field(
        default_factory=list,
        description="Workday reverse to include, if empty include all workdays",
    )
    workdays_to_exclude: list[int] = Field(
        default_factory=list,
        description="Workdays to exclude, if empty include all workdays",
    )
    workdays_reverse_to_exclude: list[int] = Field(
        default_factory=list,
        description="Workday reverse to exclude, if empty include all workdays",
    )
    keep_only_eom: bool = Field(default=False)
    exclude_holidays: bool = Field(default=False, description="Exclude holidays")
    exclude_weekends: bool = Field(default=False, description="Exclude weekends")
    only_keep_workdays: bool = Field(default=False, description="Only keep workdays, exclude holidays and weekends")
    counterparties_to_keep: list[str] = Field(
        default_factory=list,
        description="List of counterparty names to keep, remove everything else; if empty keep all counterparties",
    )
    counterparties_to_remove: list[str] = Field(
        default_factory=list,
        description="List of counterparty names to remove, keep everything else; if empty keep all counterparties",
    )
    remove_zero_amount: bool = Field(default=False, description="remove rows where amount is null")
    amount_col_name: str = Field(default="total_amount")


class CustomFilter(BaseTransformation):
    name: Literal["CustomFilter"] = "CustomFilter"
    display_name: str = "Custom Filter"
    description: str = """
        Filter rows based on a custom filter.
    """
    parameters: CustomFilterParameters = CustomFilterParameters()

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "CustomFilter":
        raise NotImplementedError("CustomFilter is not implemented for snowpark")

    def _fit_pandas(self, df: pd.DataFrame) -> "CustomFilter":
        columns = df.columns
        if "workday_of_month" not in columns and self.parameters.workdays_to_include:
            raise ValueError("workday_of_month column not found")
        if "workday_of_month_reverse" not in columns and self.parameters.workdays_reverse_to_include:
            raise ValueError("workday_of_month_reverse column not found")
        if "is_holiday" not in columns and self.parameters.exclude_holidays:
            raise ValueError("is_holiday column not found")
        if "is_weekend" not in columns and self.parameters.exclude_weekends:
            raise ValueError("is_weekend column not found")
        if "custom_counterparty_name" not in columns and self.parameters.counterparties_to_keep:
            raise ValueError("customer_counterparty_name not found")
        if "custom_counterparty_name" not in columns and self.parameters.counterparties_to_remove:
            raise ValueError("customer_counterparty_name not found")
        if "is_workday" not in columns and self.parameters.only_keep_workdays:
            raise ValueError("is_workday not found")
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        raise NotImplementedError("CustomFilter is not implemented for snowpark")

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.parameters.keep_only_eom:
            df = df[df["is_last_workday_of_month"]]
        if self.parameters.workdays_to_include:
            df = df[df["workday_of_month"].isin(self.parameters.workdays_to_include)]

        if self.parameters.workdays_reverse_to_include:
            df = df[df["workday_of_month_reverse"].isin(self.parameters.workdays_reverse_to_include)]

        if self.parameters.workdays_to_exclude:
            df = df[~df["workday_of_month"].isin(self.parameters.workdays_to_exclude)]

        if self.parameters.workdays_reverse_to_exclude:
            df = df[~df["workday_of_month_reverse"].isin(self.parameters.workdays_reverse_to_exclude)]

        if self.parameters.exclude_holidays:
            df = df[~df["is_holiday"]]

        if self.parameters.exclude_weekends:
            df = df[~df["is_weekend"]]

        if self.parameters.counterparties_to_keep and len(self.parameters.counterparties_to_keep) > 1:
            df = df[df["custom_counterparty_name"].str.lower().isin(self.parameters.counterparties_to_keep)]

        if self.parameters.counterparties_to_remove and len(self.parameters.counterparties_to_remove):
            filter_counterparties = (
                df["custom_counterparty_name"].str.lower().isin(self.parameters.counterparties_to_remove)
            )
            df = df[~filter_counterparties]

        if self.parameters.remove_zero_amount:
            df = df[df[self.parameters.amount_col_name] != 0]

        if self.parameters.only_keep_workdays:
            df = df[df["is_workday"]]
        return df

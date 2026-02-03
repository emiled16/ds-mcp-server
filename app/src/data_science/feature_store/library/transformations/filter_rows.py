from typing import Any, Literal

import pandas as pd
from pydantic import Field

from src.data_science.compat import SnowparkDataFrame
from src.data_science.ds_core.atomic_functions.pandas.filter_rows import filter_rows as pandas_filter_rows
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class FilterRowsParameters(BaseParameter):
    column: str = Field(
        description="Column name to filter on",
    )
    operator: str = Field(
        description="""
        Comparison operator to use for filtering. 
        Supported operators: '==', '!=', '>', '<', '>=', '<=', 'contains', 'startswith', 'endswith'
        """,
    )
    value: Any = Field(
        description="Value to compare against",
    )


class FilterRows(BaseTransformation):
    name: Literal["FilterRows"] = "FilterRows"
    display_name: str = "Filter Rows"
    description: str = "Filter rows in a dataframe based on a column, operator and value condition"
    parameters: FilterRowsParameters = Field(
        description="Filter rows parameters",
        # default=FilterRowsParameters(),
    )

    def _validate(self, df: pd.DataFrame | SnowparkDataFrame) -> "FilterRows":
        if self.parameters.column not in df.columns:
            raise ValueError(f"Column {self.parameters.column} not found in dataframe")

        valid_operators = ["==", "!=", ">", "<", ">=", "<=", "contains", "startswith", "endswith"]
        if self.parameters.operator not in valid_operators:
            raise ValueError(f"Unsupported operator: {self.parameters.operator}")

        return self

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "FilterRows":
        return self

    def _fit_pandas(self, df: pd.DataFrame) -> "FilterRows":
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        pass

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        self._validate(df)
        if not self.is_fitted:
            raise ValueError("Transformation is not fitted")

        return pandas_filter_rows(
            df=df, column=self.parameters.column, operator=self.parameters.operator, value=self.parameters.value
        )

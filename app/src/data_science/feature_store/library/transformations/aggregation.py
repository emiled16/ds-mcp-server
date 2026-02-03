from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.ds_core.atomic_functions.pandas.aggregate import aggregate as pandas_aggregate
from src.data_science.ds_core.definitions.orchestration.transformation import (
    BaseParameter,
    BaseTransformation,
)


class AggregationParameters(BaseParameter):
    dimensions: list[str] = Field(
        description="Dimensions to aggregate by",
        default=[],
    )
    aggregations: list[tuple[str, str, str] | tuple[str, str]] = Field(
        description="""
        Aggregation to perform. List of tuples of strings (column_name, aggregation_function, new_column_name)
        Example: [("column_name", "sum", "new_column_name")]

        Can also be provided as a list of tuples of strings (column_name, aggregation_function)
        Example: [("column_name", "sum")] # in this case, the new column name will be the aggregation function name
        Result: new_column_name = "sum_column_name"
        """,
        default=[],
    )


class Aggregation(BaseTransformation):
    name: Literal["Aggregation"] = "Aggregation"
    display_name: str = "Aggregation"
    description: str = "Aggregate a dataframe by dimensions and perform an aggregation"
    parameters: AggregationParameters = Field(
        description="Aggregation parameters",
        default=AggregationParameters(),
    )

    @staticmethod
    def _validate_dimensions(dimensions: list[str], columns: list[str]) -> bool:
        if not dimensions:
            return True
        return all(dim in columns for dim in dimensions)

    @staticmethod
    def _validate_aggregation(
        aggregations: list[tuple[str, str, str] | tuple[str, str]],
        columns: list[str],
    ) -> bool:
        condition1 = all(agg[0] in columns for agg in aggregations)
        # TODO: check if aggregation is valid
        condition2 = True
        return condition1 and condition2

    def _validate(self, df: pd.DataFrame) -> "Aggregation":
        if not self._validate_dimensions(self.parameters.dimensions, columns=list(df.columns)):
            raise ValueError("Dimensions are not valid")
        if not self._validate_aggregation(self.parameters.aggregations, columns=list(df.columns)):
            raise ValueError("Aggregations are not valid")
        return self

    def _fit_pandas(self, df: pd.DataFrame) -> "Aggregation":
        return self

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        self._validate(df)
        if not self.is_fitted:
            raise ValueError("Transformation is not fitted")

        return pandas_aggregate(
            df=df,
            dimensions=self.parameters.dimensions,
            aggregations=self.parameters.aggregations,
        )

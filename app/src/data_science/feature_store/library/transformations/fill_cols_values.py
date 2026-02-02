from typing import Literal

import pandas as pd
from pydantic import Field
from snowflake.snowpark import DataFrame as SnowparkDataFrame

from src.data_science.ds_core.definitions.orchestration.transformation import (
    BaseParameter,
    BaseTransformation,
)


class FillColsValuesParameters(BaseParameter):
    group_by: list[str] = Field(default=[])
    order_by: list[str] = Field(default=[])
    how_to_fill: dict[
        str,
        Literal[
            "ffill",
            "bfill",
            "interpolate",
            "zero",
            "mean",
            "median",
            "mode",
            "min",
            "max",
        ],
    ] = Field(default=dict)


class FillColsValues(BaseTransformation):
    name: Literal["FillColsValues"] = "FillColsValues"
    display_name: str = "Fill Columns with Values"
    description: str = """
        Fill the values of the columns with the mean, median, or mode of the values.
    """
    parameters: FillColsValuesParameters

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "FillColsValues":
        pass

    def _fit_pandas(self, df: pd.DataFrame) -> "FillColsValues":
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        pass

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        indexes = df.index.names
        df = df.reset_index()
        res = df.copy(deep=True)

        # print("__________________________________________________________________")
        # print(res[res.duplicated()])
        # print(res.duplicated().head())
        # print(res[res.duplicated()].date.unique())
        # print("__________________________________________________________________")

        df_grouped = res.groupby(self.parameters.group_by) if self.parameters.group_by else res

        for column, how_to_fill in self.parameters.how_to_fill.items():
            match how_to_fill:
                case "ffill":
                    # res[column] = df_grouped.apply(
                    #     lambda x: x.sort_values(self.parameters.order_by)[column].ffill()
                    # ).reset_index(drop=True)
                    s: pd.Series = df_grouped.apply(
                        lambda x: x.sort_values(self.parameters.order_by)[column].ffill()
                    ).reset_index(level=[0, 1], drop=True)
                    res[column] = s
                case "bfill":
                    res[column] = df_grouped.apply(
                        lambda x: x.sort_values(self.parameters.order_by)[column].bfill()
                    ).reset_index(drop=True)
                case "interpolate":
                    res[column] = df_grouped.apply(
                        lambda x: x.sort_values(self.parameters.order_by)[column].interpolate()
                    ).reset_index(drop=True)
                case "zero":
                    res[column] = df_grouped[column].fillna(0)
                case "mean":
                    res[column] = df_grouped.apply(
                        lambda x: x.sort_values(self.parameters.order_by)[column].fillna(x[column].mean())
                    ).reset_index(drop=True)
                case "median":
                    res[column] = df_grouped.apply(
                        lambda x: x.sort_values(self.parameters.order_by)[column].fillna(x[column].median())
                    ).reset_index(drop=True)
                case "mode":
                    res[column] = df_grouped.apply(
                        lambda x: x.sort_values(self.parameters.order_by)[column].fillna(x[column].mode())
                    ).reset_index(drop=True)
                case "min":
                    res[column] = df_grouped.apply(
                        lambda x: x.sort_values(self.parameters.order_by)[column].fillna(x[column].min())
                    ).reset_index(drop=True)
                case "max":
                    res[column] = df_grouped.apply(
                        lambda x: x.sort_values(self.parameters.order_by)[column].fillna(x[column].max())
                    ).reset_index(drop=True)
                case _:
                    raise ValueError(f"Invalid how_to_fill: {how_to_fill}")

        res = res.drop_duplicates().reset_index(drop=True)

        return res.set_index(indexes)

from typing import Literal, Union

import pandas as pd
from pydantic import Field
from snowflake.snowpark import DataFrame as SnowparkDataFrame

from src.data_science.ds_core.definitions.orchestration.io import BaseInput
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class MergeParameters(BaseParameter):
    left_index: bool = Field(default=False, description="Left index column")
    right_index: bool = Field(default=False, description="Right index column")
    left_on: list[str] = Field(default=[], description="Left columns to merge")
    right_on: list[str] = Field(default=[], description="Right columns to merge")
    how: Literal["left", "right", "inner", "outer"] = Field(default="left", description="How to merge")


class Merge(BaseTransformation):
    name: Literal["Merge"] = "Merge"
    display_name: str = "Merge"
    description: str = "Merge 2 dataframes"
    inputs: list[BaseInput] = Field(
        default=[
            BaseInput(name="left", description="Left dataframe to merge"),
            BaseInput(
                name="right",
                description="Right dataframe to merge",
                type=Union[pd.DataFrame, SnowparkDataFrame],
            ),
        ],
    )
    parameters: MergeParameters = MergeParameters()

    def _fit_snowpark(self, left: SnowparkDataFrame, right: SnowparkDataFrame) -> "Merge":
        raise NotImplementedError("Merge is not implemented for snowpark")

    def _fit_pandas(self, left: pd.DataFrame, right: pd.DataFrame) -> "Merge":
        return self

    def _transform_snowpark(self, left: SnowparkDataFrame, right: SnowparkDataFrame) -> SnowparkDataFrame:
        raise NotImplementedError("Merge is not implemented for snowpark")

    def _transform_pandas(self, left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
        # find common columns between left and right
        common_columns = set(left.columns) & set(right.columns)

        # TODO: finder a cleverer way to do this
        params = {}
        if common_columns:
            right = right.drop(columns=list(common_columns))
        if self.parameters.left_index:
            params["left_index"] = self.parameters.left_index
        if self.parameters.right_index:
            params["right_index"] = self.parameters.right_index
        if self.parameters.left_on:
            params["left_on"] = self.parameters.left_on
        if self.parameters.right_on:
            params["right_on"] = self.parameters.right_on
        return left.merge(right, how=self.parameters.how, **params)

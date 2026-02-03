from typing import Any, Literal, Union

import pandas as pd
from pydantic import Field
from src.data_science.compat import SnowparkDataFrame

from src.data_science.ds_core.atomic_functions.pandas.concatenate import concatenate as pandas_concatenate
from src.data_science.ds_core.atomic_functions.snowpark.concatenate import concatenate as snowpark_concatenate
from src.data_science.ds_core.definitions.orchestration.transformation import (
    BaseInput,
    BaseParameter,
    BaseTransformation,
)


class ConcatInput1(BaseInput):
    name: str = Field(default="df")
    description: str = Field(default="Dataframe to transform")
    type: Any = Field(
        description="Type of the input",
        default=Union[pd.DataFrame, SnowparkDataFrame],
    )


class ConcatInput2(BaseInput):
    name: str = Field(default="df2")
    description: str = Field(default="Dataframe to transform")
    type: Any = Field(
        description="Type of the input",
        default=Union[pd.DataFrame, SnowparkDataFrame],
    )


class Concat(BaseTransformation):
    name: Literal["Concat"] = "Concat"
    display_name: str = "Concatenate Dataframes"
    description: str = (
        "Concatenate multiple dataframes (at the moment only two dfs can be concatenated at the same time)"
    )
    parameters: BaseParameter = Field(default=BaseParameter())
    inputs: list[BaseInput] = Field(default=[ConcatInput1(), ConcatInput2()])
    # parameters: ConcatParameters = Field(description="Concat parameters")

    def _fit_snowpark(self, **dfs: SnowparkDataFrame) -> "Concat":
        return self

    def _fit_pandas(self, **dfs: pd.DataFrame) -> "Concat":
        return self

    def _validate(self, **dfs: Union[pd.DataFrame, SnowparkDataFrame]) -> "Concat":
        for df in dfs.values():
            if not isinstance(df, (pd.DataFrame, SnowparkDataFrame)):
                raise ValueError("All dataframes must be of type pd.DataFrame or SnowparkDataFrame")

        first_df = next(iter(dfs.values()))
        if isinstance(first_df, SnowparkDataFrame):
            self._validate_snowpark(**dfs)
        elif isinstance(first_df, pd.DataFrame):
            self._validate_pandas(**dfs)
        return self

    def _validate_snowpark(self, **dfs: SnowparkDataFrame) -> "Concat":
        lengths = [df.count().collect()[0][0] for df in dfs.values()]
        if not all(length == lengths[0] for length in lengths):
            raise ValueError("All dataframes must have the same number of rows")
        return self

    def _validate_pandas(self, **dfs: pd.DataFrame) -> "Concat":
        lengths = [len(df) for df in dfs.values()]
        if not all(length == lengths[0] for length in lengths):
            raise ValueError("All dataframes must have the same number of rows")
        return self

    def _transform_snowpark(self, **dfs: SnowparkDataFrame) -> SnowparkDataFrame:
        return snowpark_concatenate(**dfs)

    def _transform_pandas(self, **dfs: pd.DataFrame) -> pd.DataFrame:
        return pandas_concatenate(**dfs)

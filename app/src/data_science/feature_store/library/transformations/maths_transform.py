from typing import Literal

import pandas as pd
from pydantic import Field
from snowflake.snowpark import DataFrame as SnowparkDataFrame

from src.data_science.ds_core.atomic_functions.pandas.maths_transform import maths_transform as pandas_maths_transform
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class MathsTransformParameters(BaseParameter):
    columns: list[str] = Field(default=[])
    transform: Literal["square", "cube", "sqrt", "log", "inverse", "inverse_sqrt", "inverse_square"] = Field(
        default="square",
    )


class MathsTransform(BaseTransformation):
    name: Literal["MathsTransform"] = "MathsTransform"
    display_name: str = "Apply Mathematical Transformations"
    description: str = """
        Apply a mathematical transformation to the specified columns.
    """
    parameters: MathsTransformParameters

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "MathsTransform":
        pass

    def _fit_pandas(self, df: pd.DataFrame) -> "MathsTransform":
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        pass

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return pandas_maths_transform(df, self.parameters.columns, self.parameters.transform)

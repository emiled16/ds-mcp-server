from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.ds_core.atomic_functions.pandas.feature_cyclical_time_periods import (
    cyclical_time_transform as pandas_cyclical_time_transform,
)
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class CyclicalTimeTransformParameters(BaseParameter):
    datetime_column: str = Field(default="", description="Column to transform")
    granularity: Literal["week", "month", "quarter"] = Field(
        default="month", description="Granularity of the cyclical transform"
    )


class CyclicalTimeTransform(BaseTransformation):
    name: Literal["CyclicalTimeTransform"] = "CyclicalTimeTransform"
    display_name: str = "Cyclical Time Transform"
    description: str = """
        Transform a datetime column into cyclical features.
        The datetime column is first converted to a datetime object and then transformed into cyclical features.
        The resulting dataframe will have the original datetime column plus the new cyclical features.
    """
    parameters: CyclicalTimeTransformParameters

    def _fit_pandas(self, df: pd.DataFrame) -> "CyclicalTimeTransform":
        return self

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return pandas_cyclical_time_transform(df, self.parameters.datetime_column, self.parameters.granularity)

from typing import Literal

import pandas as pd
from pydantic import Field
from snowflake.snowpark import DataFrame as SnowparkDataFrame

from src.data_science.ds_core.atomic_functions.pandas.maths_transform import (
    polynomial_features as pandas_polynomial_features,
)
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class PolynomialFeaturesParameters(BaseParameter):
    columns: list[str] = Field(default_factory=list, description="The columns to transform")
    degree: int = Field(default=2, description="The degree of the polynomial")
    include_bias: bool = Field(default=True, description="Whether to include the bias term")
    interaction_only: bool = Field(default=False, description="Whether to only include interaction terms")


class PolynomialFeatures(BaseTransformation):
    name: Literal["PolynomialFeatures"] = "PolynomialFeatures"
    display_name: str = "Generate Polynomial Features"
    description: str = "Generate polynomial features"
    parameters: PolynomialFeaturesParameters

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "PolynomialFeatures":
        pass

    def _fit_pandas(self, df: pd.DataFrame) -> "PolynomialFeatures":
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        pass

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return pandas_polynomial_features(
            df,
            self.parameters.columns,
            self.parameters.degree,
            self.parameters.include_bias,
            self.parameters.interaction_only,
        )

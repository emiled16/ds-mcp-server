from typing import Literal, Union

import pandas as pd
from pydantic import Field
from snowflake.snowpark import DataFrame as SnowparkDataFrame

from src.data_science.ds_core.atomic_functions.pandas.drop_outliers import drop_rare_labels as drop_rare_labels_pandas
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class DropRareLabelsParameters(BaseParameter):
    """
    Parameters for dropping rows with rare categorical labels.
    """

    columns: list[str] = Field(
        description="List of categorical/string columns to check for rare labels",
        default_factory=list,
    )
    min_frequency: float = Field(
        description="Minimum frequency threshold - labels appearing less frequently will be dropped",
        default=0.01,
    )


class DropRareLabels(BaseTransformation):
    name: Literal["DropRareLabels"] = "DropRareLabels"
    display_name: str = "Drop Labels with Low Frequency"
    description: str = "Drop rows containing rare categorical labels from a dataframe"
    parameters: DropRareLabelsParameters

    def _fit(self, _df: Union[pd.DataFrame, SnowparkDataFrame]) -> "DropRareLabels":
        return self

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "DropRareLabels":
        return self._fit(df)

    def _fit_pandas(self, df: pd.DataFrame) -> "DropRareLabels":
        return self._fit(df)

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return drop_rare_labels_pandas(
            df,
            self.parameters.columns,
            self.parameters.min_frequency,
        )

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        pass

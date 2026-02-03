from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.ds_core.atomic_functions.pandas.drop_outliers import drop_outliers_iqr as drop_outliers_iqr_pandas
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class DropOutliersIQRParameters(BaseParameter):
    """
    Parameters for dropping outliers from a dataframe using IQR method.
    """

    columns: list[str] = Field(
        description="Columns to check for outliers",
        default_factory=list,
    )


class DropOutliersIQR(BaseTransformation):
    name: Literal["DropOutliersIQR"] = "DropOutliersIQR"
    display_name: str = "Drop Outliers using IQR"
    description: str = "Drop rows containing outlier values from a dataframe using IQR method"
    parameters: DropOutliersIQRParameters

    def _fit(self, _df: pd.DataFrame) -> "DropOutliersIQR":
        return self

    def _fit_pandas(self, df: pd.DataFrame) -> "DropOutliersIQR":
        return self._fit(df)

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return drop_outliers_iqr_pandas(df, self.parameters.columns)

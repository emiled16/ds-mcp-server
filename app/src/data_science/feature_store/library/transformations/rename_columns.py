from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.ds_core.atomic_functions.pandas.rename_cols import rename_cols as rename_cols_pandas
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class RenameColumnsParameters(BaseParameter):
    """
    replicate same behavior as pandas, for instance:
    - df.rename(columns={'old_name': 'new_name'})
    - df.rename(columns={'old_name': 'new_name', 'old_name2': 'new_name2'})
    """

    columns: dict[str, str] = Field(
        description="Columns to rename, e.g. {'old_name': 'new_name'}",
        default_factory=dict,
    )


class RenameColumns(BaseTransformation):
    name: Literal["RenameColumns"] = "RenameColumns"
    display_name: str = "Rename Columns"
    description: str = "Rename columns of a dataframe"
    parameters: RenameColumnsParameters = Field(default=RenameColumnsParameters())

    def _fit(self, _df: pd.DataFrame) -> "RenameColumns":
        return self

    def _fit_pandas(self, df: pd.DataFrame) -> "RenameColumns":
        return self._fit(df)

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        return rename_cols_pandas(df, self.parameters.columns)

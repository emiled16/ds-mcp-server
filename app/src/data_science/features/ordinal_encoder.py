from typing import Literal

import numpy as np
import pandas as pd
from pydantic import Field
from sklearn.preprocessing import OrdinalEncoder as SklearnOrdinalEncoder
from src.data_science.compat import SnowparkDataFrame

from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class OrdinalEncoderParameters(BaseParameter):
    column: str = Field(default="", description="Column to encode")


class OrdinalEncoder(BaseTransformation):
    name: Literal["OrdinalEncoder"] = "OrdinalEncoder"
    display_name: str = "Ordinal Encoder"
    description: str = """
       Encodes the specified column as a ordinal encoded column.
       The column will be transformed into a categorical type with integer codes.
    """
    parameters: OrdinalEncoderParameters = OrdinalEncoderParameters()
    encoder: SklearnOrdinalEncoder | None = Field(default=None, exclude=True)

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "OrdinalEncoder":
        raise NotImplementedError("OrdinalEncoder is not implemented for snowpark")

    def _fit_pandas(self, df: pd.DataFrame) -> "OrdinalEncoder":
        if self.parameters.column not in df.columns:
            raise ValueError(f"Column {self.parameters.column} not found in dataframe")

        self.encoder = SklearnOrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)

        self.encoder.fit(df[self.parameters.column].unique().reshape(-1, 1))
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        raise NotImplementedError("OrdinalEncoder is not implemented for snowpark")

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.encoder is None:
            raise ValueError("Encoder not fitted")
        df = df.copy()
        df[f"ordinal_encode__{self.parameters.column}"] = self.encoder.transform(
            df[self.parameters.column].values.reshape(-1, 1)
        )
        df[f"ordinal_encode__{self.parameters.column}"] = df[f"ordinal_encode__{self.parameters.column}"].astype(
            "category"
        )
        return df

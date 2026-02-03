from typing import Literal

import pandas as pd
from pydantic import Field
from sklearn.preprocessing import OneHotEncoder

from src.data_science.compat import SnowparkDataFrame
from src.data_science.ds_core.atomic_functions.pandas.encode_str import (
    encode_one_hot as pandas_encode_one_hot,
)
from src.data_science.ds_core.definitions.orchestration.transformation import (
    BaseParameter,
    BaseTransformation,
)


class EncodeOneHotParameters(BaseParameter):
    column: str = Field(default="", description="Column to encode")
    threshold: float | None = Field(default=None, description="Threshold of frequency to encode")
    drop_original_column: bool = Field(default=True, description="Drop the original column")


class EncodeOneHot(BaseTransformation):
    name: Literal["EncodeOneHot"] = "EncodeOneHot"
    display_name: str = "Encode One Hot"
    description: str = """
        Encode the columns specified in `columns` as one-hot encoded columns.
        If `threshold` is provided, only the columns with a frequency greater than the threshold will be encoded.
        If `drop_original_column` is True, the original column will be dropped.
    """
    parameters: EncodeOneHotParameters
    encoder: OneHotEncoder | None = Field(default=None)

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "EncodeOneHot":
        pass

    def _fit_pandas(self, df: pd.DataFrame) -> "EncodeOneHot":
        if self.parameters.threshold is not None:
            _, encoder = pandas_encode_one_hot(df, self.parameters.column, threshold=self.parameters.threshold)
        else:
            _, encoder = pandas_encode_one_hot(df, self.parameters.column)
        self.encoder = encoder
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        pass

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        ## should the corresponding atomic function be different using fit and transform?
        if self.encoder is None:
            raise ValueError("Encoder not fitted")

        indexes = df.index.names
        df = df.reset_index()
        return pd.concat(
            [
                df,
                pd.DataFrame(
                    self.encoder.transform(df[[self.parameters.column]]),
                    columns=self.encoder.get_feature_names_out(),
                ),
            ],
            axis=1,
        ).set_index(indexes)

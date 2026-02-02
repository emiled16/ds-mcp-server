from typing import Literal, Optional

import pandas as pd
from pydantic import Field
from sklearn.decomposition import PCA
from snowflake.snowpark import DataFrame as SnowparkDataFrame

from src.data_science.ds_core.atomic_functions.pandas.feature_reduction import pca_reduction as pandas_pca_reduction
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class ReductionPCAParameters(BaseParameter):
    columns: list[str] = Field(default=[])
    n_components: int = Field(default=3)


class ReductionPCA(BaseTransformation):
    name: Literal["ReductionPCA"] = "ReductionPCA"
    display_name: str = "Create Principal Components"
    description: str = """
        Create principal components from the dataframe.
    """
    parameters: ReductionPCAParameters
    pca_transformer: Optional[PCA] = None

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "ReductionPCA":
        pass

    def _fit_pandas(self, df: pd.DataFrame) -> "ReductionPCA":
        _, pca_transformer = pandas_pca_reduction(df, self.parameters.columns, self.parameters.n_components)
        self.pca_transformer = pca_transformer
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        pass

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.pca_transformer is None:
            raise ValueError("PCA transformer not fitted")

        return pd.concat(
            [
                df.reset_index(drop=True),
                pd.DataFrame(
                    self.pca_transformer.transform(df[self.pca_transformer.feature_names_in_]),
                    columns=self.pca_transformer.get_feature_names_out(),
                ).reset_index(drop=True),
            ],
            axis=1,
        )

from typing import Literal

import pandas as pd
from pydantic import Field
from sklearn.cluster import FeatureAgglomeration as SKLearnFeatureAgglomeration

from src.data_science.ds_core.atomic_functions.pandas.feature_reduction import (
    feature_agglomeration as pandas_feature_agglomeration,
)
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class FeatureAgglomerationParameters(BaseParameter):
    columns: list[str] = Field(default=[])
    n_clusters: int = Field(default=3)
    metric: Literal["euclidean"] = Field(default="euclidean")  # because ward is the chosen linkage


class FeatureAgglomeration(BaseTransformation):
    name: Literal["FeatureAgglomeration"] = "FeatureAgglomeration"
    display_name: str = "Feature Agglomeration"
    description: str = """
        Agglomerate features into a single feature.
    """
    parameters: FeatureAgglomerationParameters
    agglomeration_transformer: SKLearnFeatureAgglomeration | None = None

    def _fit_pandas(self, df: pd.DataFrame) -> "FeatureAgglomeration":
        _, agglomeration_transformer = pandas_feature_agglomeration(
            df,
            self.parameters.columns,
            self.parameters.n_clusters,
            self.parameters.metric,
        )
        if agglomeration_transformer is None:
            raise ValueError("FeatureAgglomeration has not been fitted")
        self.agglomeration_transformer = agglomeration_transformer
        return self

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.agglomeration_transformer is None:
            raise ValueError("FeatureAgglomeration has not been fitted")

        return pd.concat(
            [
                df.reset_index(drop=True),
                pd.DataFrame(
                    self.agglomeration_transformer.transform(df[self.agglomeration_transformer.feature_names_in_]),
                    columns=self.agglomeration_transformer.get_feature_names_out(),
                ).reset_index(drop=True),
            ],
            axis=1,
        )

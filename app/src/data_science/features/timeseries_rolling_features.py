from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.compat import SnowparkDataFrame
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class RollingFeaturesParameters(BaseParameter):
    window_sizes: list[int] = Field(default=[7], description="Window sizes for rolling averages")
    target_column: str = Field(default="", description="Target column to calculate rolling averages on")
    target_column_transformations: list[
        Literal["mean", "sum", "min", "max", "std", "var", "count", "first", "last"]
    ] = Field(
        default=["mean"],
        description="Transformation to apply to the target column",
    )
    suffix: str = Field(default="", description="Suffix to add to the rolling features")
    partition_columns: list[str] = Field(default=[], description="Partition columns to calculate rolling averages on")
    order_by_columns: list[str] = Field(default=[], description="Order by columns to calculate rolling averages on")
    fillna: bool = Field(default=True, description="Fill NANs with 0s")


class RollingFeatures(BaseTransformation):
    name: Literal["RollingFeatures"] = "RollingFeatures"
    display_name: str = "Rolling Features"
    description: str = """
        Transform a datetime column into rolling features.
    """
    parameters: RollingFeaturesParameters = RollingFeaturesParameters()

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "RollingFeatures":
        return self

    def _fit_pandas(self, df: pd.DataFrame) -> "RollingFeatures":
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        raise NotImplementedError("RollingFeatures is not implemented for snowpark")

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        indexes = df.index.names
        df = df.reset_index()
        for window_size in self.parameters.window_sizes:
            for transformation in self.parameters.target_column_transformations:
                name = (
                    f"rolling_{transformation}_{self.parameters.target_column}_{window_size}_{self.parameters.suffix}"
                )
                ds = (
                    df.groupby(self.parameters.partition_columns)
                    .apply(
                        lambda x, k=window_size, tf=transformation: x.sort_values(self.parameters.order_by_columns)
                        .set_index(self.parameters.order_by_columns)
                        .rolling(window=k, closed="left")
                        .agg({self.parameters.target_column: tf}),
                    )
                    .rename(columns={self.parameters.target_column: name})
                    .reset_index()[[*self.parameters.partition_columns, *self.parameters.order_by_columns, name]]
                )
                if self.parameters.fillna:
                    ds[name] = ds[name].fillna(0)
                df = df.merge(ds, on=[*self.parameters.partition_columns, *self.parameters.order_by_columns])

        return df.set_index(indexes)

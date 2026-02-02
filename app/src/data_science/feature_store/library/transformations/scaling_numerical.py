from typing import Literal, Optional, Union

import pandas as pd
from pydantic import Field
from sklearn.preprocessing import MinMaxScaler, PowerTransformer, RobustScaler, StandardScaler
from snowflake.snowpark import DataFrame as SnowparkDataFrame

from src.data_science.ds_core.atomic_functions.pandas.scaling_numerical import scale_data as pandas_scale_data
from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class ScalingNumericalParameters(BaseParameter):
    columns: list[str] = Field(default_factory=list, description="The columns to scale")
    method: Literal["standard", "robust", "minmax", "box-cox"] = Field(
        default="standard", description="The method to use for scaling"
    )
    overwrite_columns: bool = Field(default=True)


class ScalingNumerical(BaseTransformation):
    name: Literal["ScalingNumerical"] = "ScalingNumerical"
    display_name: str = "Scale Numerical Columns"
    description: str = "Scale numerical columns"
    parameters: ScalingNumericalParameters
    scaler: Optional[Union[MinMaxScaler, StandardScaler, RobustScaler, PowerTransformer]] = Field(default=None)

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "ScalingNumerical":
        pass

    def _fit_pandas(self, df: pd.DataFrame) -> "ScalingNumerical":
        _, scaler = pandas_scale_data(df, self.parameters.columns, self.parameters.method)
        self.scaler = scaler
        return self

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        pass

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.scaler is None:
            raise ValueError("Scaler not fitted")

        # Scale the columns
        scaled_data = self.scaler.transform(df[self.parameters.columns])
        
        # Create result dataframe
        result_df = df.copy()
        
        if self.parameters.overwrite_columns:
            # Overwrite original columns with scaled values
            result_df[self.parameters.columns] = scaled_data
        else:
            # Add new columns with _scaled suffix
            for i, col in enumerate(self.parameters.columns):
                result_df[f"{col}_scaled"] = scaled_data[:, i]

        return result_df

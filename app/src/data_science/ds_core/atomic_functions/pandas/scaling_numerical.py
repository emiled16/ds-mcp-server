from typing import Literal, Union

import pandas as pd
from sklearn.preprocessing import MinMaxScaler, PowerTransformer, RobustScaler, StandardScaler


def scale_data(
    df: pd.DataFrame,
    columns: list[str],
    method: Literal["standard", "robust", "minmax", "box-cox"] = "standard",
) -> tuple[pd.DataFrame, Union[StandardScaler, RobustScaler, MinMaxScaler]]:
    """
    Scale numeric columns in a dataframe using specified scaling method.

    Args:
        df: The dataframe containing columns to scale.
        columns: List of columns to scale. Only numeric columns will be scaled.
        method: Scaling method to use - one of 'standard', 'robust', or 'minmax'. Default is 'standard'.
            - standard: StandardScaler (zero mean and unit variance)
            - robust: RobustScaler (removes median and scales using quantiles)
            - minmax: MinMaxScaler (scales to a fixed range 0-1)
            - box-cox: PowerTransformer (scales using Box-Cox transformation)
    Returns:
        tuple[pd.DataFrame, Union[StandardScaler, RobustScaler, MinMaxScaler]]:
            - DataFrame with scaled numeric columns. Non-numeric columns are left unchanged.
            - The fitted scaler object used for the transformation. Returns None if no columns were scaled.
    """
    if len(columns) == 0:
        return df, None

    match method:
        case "standard":
            scaler = StandardScaler()
        case "robust":
            scaler = RobustScaler()
        case "minmax":
            scaler = MinMaxScaler()
        case "box-cox":
            scaler = PowerTransformer(method="box-cox")

    # Validate numeric columns
    numeric_columns = [col for col in columns if pd.api.types.is_numeric_dtype(df[col])]

    if numeric_columns:
        scaler.set_output(transform="pandas")
        df_scaled = scaler.fit_transform(df[numeric_columns])
        df_scaled.columns = [col + "_scaled" for col in df_scaled.columns]
        df = pd.concat([df, df_scaled], axis=1)

    return df, scaler

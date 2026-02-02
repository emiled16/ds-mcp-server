from typing import Literal

import pandas as pd
from pandas.api.types import is_numeric_dtype, is_string_dtype


def fill_cols_values(
    df: pd.DataFrame,
    columns: list[str],
    method: Literal["mean", "median", "mode"],
) -> pd.DataFrame:
    """
    Fill missing values in specified columns using mean/median for numeric columns and mode for string columns.

    Args:
        df: The dataframe to fill missing values in.
        method: Method to fill numeric columns - either 'mean' or 'median'. Default is 'mean'.
        columns: List of columns to fill. If None, fills all columns. Default is None.

    Returns:
        pd.DataFrame: DataFrame with missing values filled.
    """
    if len(columns) == 0:
        return df

    df_filled = df.copy()

    for col in columns:
        if is_numeric_dtype(df[col]) and method == "mean":
            fill_value = df[col].mean()
        elif is_numeric_dtype(df[col]) and method == "median":
            fill_value = df[col].median()
        elif (is_string_dtype(df[col]) or isinstance(df[col].dtype, pd.CategoricalDtype)) and method == "mode":
            fill_value = df[col].mode().iloc[0] if not df[col].mode().empty else None

        df_filled[col] = df_filled[col].fillna(fill_value, axis=0)

    return df_filled

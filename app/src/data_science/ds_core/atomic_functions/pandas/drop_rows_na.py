from typing import Literal

import pandas as pd


def drop_rows_na(df: pd.DataFrame, columns: list[str], how: Literal["any", "all"] = "any") -> pd.DataFrame:
    """
    Drop rows with null values in specified columns from a dataframe.
    Args:
        df: The dataframe to drop null values from.
        columns: The columns to check for null values.
        how: The method to drop rows. If "any", drop a row if any of the specified columns contain null values.
             If "all", drop a row only if all specified columns contain null values. Default is "any".
    Returns:
        The dataframe with rows containing null values removed.
    """
    return df.dropna(subset=columns, how=how, inplace=False)

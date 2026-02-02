from typing import Literal

import pandas as pd


def drop_rows_duplicates(
    df: pd.DataFrame,
    columns: list[str],
    keep: Literal["first", "last", False] = "first",
) -> pd.DataFrame:
    """
    Drop duplicate rows from a dataframe based on specified columns.

    Args:
        df: The dataframe to drop duplicate rows from.
        columns: The columns to check for duplicates.
        keep: Which duplicates to keep. 'first' keeps first occurrence, 'last' keeps last occurrence,
              False drops all duplicates. Default is 'first'.

    Returns:
        pd.DataFrame: The dataframe with duplicate rows removed.
    """
    if len(columns) == 0:
        return df
    return df.drop_duplicates(subset=columns, keep=keep, inplace=False)

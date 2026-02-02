import pandas as pd


def select_cols(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """
    Select columns from a dataframe.
    Args:
        df: The dataframe to select columns from.
        columns: The list of columns to select.
    Returns:
        The dataframe with selected columns.
    """
    return df[columns]

import pandas as pd


def drop_cols(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Drop specified columns from a pandas DataFrame.

    Args:
        df (pd.DataFrame): Input DataFrame
        columns (list[str]): List of column names to drop

    Returns:
        pd.DataFrame: DataFrame with specified columns removed
    """
    return df.drop(columns=columns)

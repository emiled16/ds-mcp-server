import pandas as pd


def rename_cols(df: pd.DataFrame, columns: dict[str, str]) -> pd.DataFrame:
    """
    Rename columns in a dataframe.
    Args:
        df: The dataframe to rename columns.
        columns: The dictionary of old column names to new column names.
    Returns:
        The dataframe with renamed columns.
    """
    return df.rename(columns=columns)

import pandas as pd


def remove_duplicate_rows(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """
    Remove duplicate rows from a dataframe.
    Args:
        df: The dataframe to remove duplicate rows from.
        columns: The columns to use to determine if rows are duplicates.
    Returns:
        The dataframe with duplicate rows removed.
    """
    return df.drop_duplicates(subset=columns)

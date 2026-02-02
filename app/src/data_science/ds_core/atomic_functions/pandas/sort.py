import pandas as pd


def sort(df: pd.DataFrame, columns: list[str], ascending: bool = True) -> pd.DataFrame:
    """
    Sort the dataframe by the columns specified in `columns` in ascending or descending order.
    """
    return df.sort_values(by=columns, ascending=ascending)

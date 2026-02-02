import pandas as pd


def drop_cols_zero_var(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop columns with zero variance from a dataframe (i.e. when 1 unique value)

    Args:
        df: The dataframe to drop zero variance columns from.

    Returns:
        pd.DataFrame: The dataframe with zero variance columns removed.
    """
    # Get columns with only one unique value
    cols_to_drop = df.columns[df.nunique() <= 1]

    return df.drop(columns=cols_to_drop)

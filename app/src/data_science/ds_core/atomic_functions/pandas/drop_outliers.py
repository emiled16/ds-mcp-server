from typing import Optional, Union

import pandas as pd


def drop_rows_out_of_bounds(
    df: pd.DataFrame,
    column: str,
    lower_bound: Optional[float] = None,
    upper_bound: Optional[float] = None,
) -> pd.DataFrame:
    """
    Drop rows where values in specified column fall outside given bounds.

    Args:
        df: The dataframe to filter rows from
        column: Column to check values against bounds
        lower_bound: Optional minimum value to keep (inclusive)
        upper_bound: Optional maximum value to keep (inclusive)

    Returns:
        pd.DataFrame: DataFrame with rows removed that fall outside bounds
    """
    mask = pd.Series(True, index=df.index)

    if lower_bound is not None:
        mask &= df[column] >= lower_bound

    if upper_bound is not None:
        mask &= df[column] <= upper_bound

    return df[mask]


def drop_outliers_iqr(
    df: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """
    Remove outliers from specified numeric columns using the IQR (Interquartile Range) method.

    Outliers are defined as values that fall below Q1 - 1.5*IQR or above Q3 + 1.5*IQR,
    where Q1 is the 25th percentile, Q3 is the 75th percentile, and IQR = Q3 - Q1.

    Args:
        df: The dataframe to remove outliers from.
        columns: List of columns to check for outliers.

    Returns:
        pd.DataFrame: DataFrame with outliers removed.
    """
    if len(columns) == 0:
        return df

    df_clean = df.copy()

    # Apply IQR criterion to all specified columns
    for col in columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1

            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr

            df_clean = df_clean[(df_clean[col] >= lower) & (df_clean[col] <= upper)]

    return df_clean


def drop_rare_labels(
    df: pd.DataFrame,
    columns: list[str],
    min_frequency: float = 0.01,
) -> pd.DataFrame:
    """
    Remove rows where categorical columns contain rare labels (labels with low frequency).

    A label is considered rare if its frequency is below the specified threshold.
    For example, with default min_frequency=0.01, labels appearing in less than 1% of rows are removed.

    Args:
        df: The dataframe to remove rare labels from.
        columns: List of categorical columns to check for rare labels.
        min_frequency: Minimum frequency threshold (between 0 and 1) for a label to be kept.
            Default is 0.01 (1%).

    Returns:
        pd.DataFrame: DataFrame with rare label rows removed.
    """
    if len(columns) == 0 or not (0 <= min_frequency < 1):
        return df

    df_clean = df.copy()

    for col in columns:
        if pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_categorical_dtype(df[col]):
            # Calculate frequency of each unique value
            value_counts = df[col].value_counts(normalize=True)

            # Get labels that appear frequently enough
            valid_labels = value_counts[value_counts >= min_frequency].index

            # Keep only rows with frequent labels
            df_clean = df_clean[df_clean[col].isin(valid_labels)]

    return df_clean

from typing import Any, Union

import pandas as pd


def filter_rows(df: pd.DataFrame, column: str, operator: str, value: Any) -> pd.DataFrame:
    if df[column].dtype in ["int64", "float64"]:
        return filter_rows_numeric_or_bool(df, column, operator, value)
    if df[column].dtype == "bool":
        return filter_rows_bool(df, column, value)
    # generic case (string)
    return filter_rows_string(df, column, operator, value)


def filter_rows_bool(df: pd.DataFrame, column: str, value: str) -> pd.DataFrame:
    match value:
        case "True":
            return df[df[column] == True]
        case "False":
            return df[df[column] == False]


def filter_rows_numeric_or_bool(
    df: pd.DataFrame,
    column: str,
    operator: str,
    value: Union[int, float, bool],
) -> pd.DataFrame:
    """Filter rows based on a numeric or boolean column and operator.

    Args:
        df (pd.DataFrame): The DataFrame to filter.
        column (str): The column to filter.
        operator (str): The operator to use for filtering.
        value (Union[int, float, bool]): The value to filter by.

    Returns:
        pd.DataFrame: The filtered DataFrame.
    """
    match operator:
        case "==":
            return df[df[column] == value]
        case "!=":
            return df[df[column] != value]
        case ">":
            return df[df[column] > value]
        case "<":
            return df[df[column] < value]
        case ">=":
            return df[df[column] >= value]
        case "<=":
            return df[df[column] <= value]


def filter_rows_string(df: pd.DataFrame, column: str, operator: str, value: str) -> pd.DataFrame:
    """Filter rows based on a string column and operator.

    Args:
        df (pd.DataFrame): The DataFrame to filter.
        column (str): The column to filter.
        operator (str): The operator to use for filtering.
        value (str): The value to filter by.

    Returns:
        pd.DataFrame: The filtered DataFrame.
    """
    match operator:
        case "==":
            return df[df[column] == value]
        case "!=":
            return df[df[column] != value]
        case "contains":
            return df[df[column].str.contains(value, na=False)]
        case "not contains":
            return df[~df[column].str.contains(value, na=False)]

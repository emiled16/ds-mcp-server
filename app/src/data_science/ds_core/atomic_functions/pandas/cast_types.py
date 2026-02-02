from typing import Literal

import pandas as pd


class AtomicTransformationError(Exception):
    pass


def cast_types(
    df: pd.DataFrame,
    columns: list[str],
    new_type: Literal["int", "float", "str", "datetime", "category"],
) -> pd.DataFrame:
    """
    Cast specified columns to a given data type.

    Args:
        df: The dataframe to cast column types.
        columns: List of columns to cast.
        dtype: Target data type to cast to. Must be one of: 'int', 'float', 'str', 'datetime', 'category'.

    Returns:
        pd.DataFrame: DataFrame with columns cast to specified type.
    """
    if len(columns) == 0:
        return df

    for col in columns:
        if new_type == "str":
            df[col] = df[col].apply(lambda x: "" if x is None else str(x))
            df[col] = df[col].astype(str)
        elif new_type == "datetime":
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception as e:
                raise AtomicTransformationError(f"Content does not match {new_type} type") from e
        elif new_type == "category":
            df[col] = df[col].astype("category")
        elif new_type in ["int", "float"]:
            try:
                df[col] = df[col].astype(new_type)
            except Exception as e:
                raise AtomicTransformationError(f"Content does not match {new_type} type") from e
        else:
            raise AtomicTransformationError(f"Invalid type: {new_type}")
    return df

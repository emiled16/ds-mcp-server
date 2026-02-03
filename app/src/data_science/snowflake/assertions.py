from typing import Any

import pandas as pd
from src.data_science.snowflake_optional import SNOWFLAKE_AVAILABLE, SnowparkDataFrame


def _is_snowpark_df(df: Any) -> bool:
    return SNOWFLAKE_AVAILABLE and SnowparkDataFrame is not None and isinstance(df, SnowparkDataFrame)


def assert_frame_equal(
    left: pd.DataFrame | Any,
    right: pd.DataFrame | Any,
    *,
    ignore_index: bool = False,
    ignore_row_order: bool = False,
    ignore_column_order: bool = False,
    ignore_column_casing: bool = False,
    **kwargs: Any,
) -> None:
    """Same as pandas.testing.assert_frame_equal but with additional check parameters.

    See: https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.testing.assert_frame_equal.html
    """
    if _is_snowpark_df(left) or _is_snowpark_df(right):
        ignore_index = True
        ignore_column_casing = True
        kwargs["check_dtype"] = False

    if _is_snowpark_df(left):
        left = left.to_pandas()
    if _is_snowpark_df(right):
        right = right.to_pandas()

    if ignore_column_casing:
        left = left.rename(columns=str.lower)
        right = right.rename(columns=str.lower)

    if ignore_column_order:
        left = left.sort_index(axis=1)
        right = right.sort_index(axis=1)

    if ignore_row_order:
        left = left.sort_values(by=list(left.columns))
        right = right.sort_values(by=list(right.columns))

    if ignore_index or ignore_row_order:
        left = left.reset_index(drop=True)
        right = right.reset_index(drop=True)

    pd.testing.assert_frame_equal(left, right, **kwargs)

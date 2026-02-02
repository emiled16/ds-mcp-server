from typing import Any, Union

import pandas as pd
from snowflake import snowpark


def assert_frame_equal(
    left: Union[pd.DataFrame, snowpark.DataFrame],
    right: Union[pd.DataFrame, snowpark.DataFrame],
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
    if isinstance(left, snowpark.DataFrame) or isinstance(right, snowpark.DataFrame):
        ignore_index = True
        ignore_column_casing = True
        kwargs["check_dtype"] = False

    if isinstance(left, snowpark.DataFrame):
        left = left.to_pandas()
    if isinstance(right, snowpark.DataFrame):
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

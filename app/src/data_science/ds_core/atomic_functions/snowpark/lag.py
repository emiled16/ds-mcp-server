import snowflake.snowpark.functions as f
from snowflake.snowpark import DataFrame as SnowparkDataFrame
from snowflake.snowpark.window import Window


def lag(
    df: SnowparkDataFrame,
    lags: dict[str, list[int]],
    order_by: list[str],
    partition_by: list[str],
) -> SnowparkDataFrame:
    """
    Apply lag to the dataframe.
    Args:
        df: The dataframe to apply lag to.
        lags: The lags to apply to each column, e.g. {'column_name': [1, 2]} will create two new columns
            with the original column name suffixed with _lag_1 and _lag_2.
        order_by: The columns to sort by.
        partition_by: The columns to partition by.
    Returns:
        The dataframe with the new lagged columns.
    """
    for column, lag_windows in lags.items():
        for lag_window in lag_windows:
            func = f.lag if lag_window > 0 else f.lead
            df = df.with_column_renamed(
                f"{column}_lag_{lag_window}",
                func(column, lag_window).over(Window.partition_by(partition_by).order_by(order_by)),
            )
    return df

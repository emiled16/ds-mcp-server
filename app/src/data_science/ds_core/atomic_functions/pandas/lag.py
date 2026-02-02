import pandas as pd


def lag(
    df: pd.DataFrame,
    lags: dict[str, list[int]],
    order_by: list[str],
    partition_by: list[str],
    fillna: bool = True,
    suffix: str | None = None,
) -> pd.DataFrame:
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
    new_df = df.copy(deep=True).sort_values([*partition_by, *order_by])
    for column, lag_windows in lags.items():
        for lag_window in lag_windows:
            name = f"{column}_lag_{lag_window}"
            if suffix:
                name = f"{name}_{suffix}"

            df_grouped = new_df.groupby(partition_by)

            df_applied = df_grouped.apply(
                lambda x: x.sort_values(order_by).set_index(order_by)[[column]].shift(lag_window)
            )

            df_renamed = df_applied.rename(columns={column: name})

            df_reset_index = df_renamed.reset_index()

            ds = df_reset_index[[*partition_by, *order_by, name]]

            new_df = new_df.merge(ds, on=[*partition_by, *order_by])

            if fillna:
                new_df[name] = new_df[name].fillna(0)
    return new_df

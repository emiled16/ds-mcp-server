from snowflake.snowpark import DataFrame as SnowparkDataFrame


def drop_cols(
    df: SnowparkDataFrame,
    columns: list[str],
) -> SnowparkDataFrame:
    """
    Drop columns from a dataframe.
    """
    return df.drop(*columns)

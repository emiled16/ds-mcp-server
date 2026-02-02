from snowflake.snowpark import DataFrame as SnowparkDataFrame


def rename_cols(df: SnowparkDataFrame, columns: dict[str, str]) -> SnowparkDataFrame:
    """
    Rename columns in a dataframe.
    Args:
        df: The dataframe to rename columns.
        columns: The dictionary of old column names to new column names.
    Returns:
        The dataframe with renamed columns.
    """
    return df.rename(columns=columns)

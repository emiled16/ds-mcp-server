from snowflake.snowpark import DataFrame as SnowparkDataFrame


def remove_duplicate_rows(df: SnowparkDataFrame, columns: list[str]) -> SnowparkDataFrame:
    """
    Remove duplicate rows from a dataframe.
    Args:
        df: The dataframe to remove duplicate rows from.
        columns: The columns to use to determine if rows are duplicates.
    Returns:
        The dataframe with duplicate rows removed.
    """
    return df.drop_duplicates(subset=columns)

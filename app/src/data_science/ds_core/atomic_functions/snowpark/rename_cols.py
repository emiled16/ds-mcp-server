from src.data_science.snowflake_optional import SnowparkDataFrame, require_snowflake


def rename_cols(df: SnowparkDataFrame, columns: dict[str, str]) -> SnowparkDataFrame:
    """
    Rename columns in a dataframe.
    Args:
        df: The dataframe to rename columns.
        columns: The dictionary of old column names to new column names.
    Returns:
        The dataframe with renamed columns.
    """
    require_snowflake()
    return df.rename(columns=columns)

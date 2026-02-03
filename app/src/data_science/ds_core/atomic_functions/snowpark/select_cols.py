from src.data_science.snowflake_optional import SnowparkDataFrame, require_snowflake


def select_cols(df: SnowparkDataFrame, columns: list[str]) -> SnowparkDataFrame:
    """
    Select columns from a dataframe.
    Args:
        df: The dataframe to select columns from.
        columns: The list of columns to select.
    Returns:
        The dataframe with selected columns.
    """
    require_snowflake()
    return df.select(columns)

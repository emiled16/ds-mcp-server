from src.data_science.snowflake_optional import SnowparkDataFrame, require_snowflake


def drop_cols(
    df: SnowparkDataFrame,
    columns: list[str],
) -> SnowparkDataFrame:
    """
    Drop columns from a dataframe.
    """
    require_snowflake()
    return df.drop(*columns)

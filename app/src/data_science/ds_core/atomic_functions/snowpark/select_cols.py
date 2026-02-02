import snowflake.snowpark.functions as f
from snowflake.snowpark import DataFrame as SnowparkDataFrame


def select_cols(df: SnowparkDataFrame, columns: list[str]) -> SnowparkDataFrame:
    """
    Select columns from a dataframe.
    Args:
        df: The dataframe to select columns from.
        columns: The list of columns to select.
    Returns:
        The dataframe with selected columns.
    """
    return df.select(columns)

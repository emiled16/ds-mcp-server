from src.data_science.snowflake_optional import F as f
from src.data_science.snowflake_optional import SnowparkDataFrame, require_snowflake


def truncate_date(
    df: SnowparkDataFrame,
    date_col: str,
    truncate_to: str,
    output_col: str | None = None,
) -> SnowparkDataFrame:
    """
    Truncate a date column to a specific unit of time.
    Args:
        df: The dataframe to truncate.
        date_col: The name of the date column to truncate.
        truncate_to: The unit of time to truncate to.
        output_col: The name of the output column.
    Returns:
        The dataframe with the date column truncated.
    """
    require_snowflake()
    output_col = output_col or date_col
    return df.with_column_renamed(f.date_trunc(truncate_to, f.col(date_col)), output_col)

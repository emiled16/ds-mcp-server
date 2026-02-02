from typing import Optional

import pandas as pd


def truncate_date(
    df: pd.DataFrame,
    date_col: str,
    truncate_to: str,
    output_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Truncate a date column to a specific unit of time.
    Args:
        df: The dataframe to truncate.
        date_col: The name of the date column to truncate.
        truncate_to: The unit of time to truncate to.
    Returns:
        The dataframe with the date column truncated.
    truncate_to can be one of the following:
        - 'year'
        - 'month'
        - 'day'
        - 'hour'
        - 'minute'
        - 'second'
    """

    mapping = {
        "year": lambda x: f"{x.year}-01-01",
        "month": lambda x: f"{x.year}-{x.month:02d}-01",
        "day": lambda x: f"{x.year}-{x.month:02d}-{x.day:02d}",
        "hour": lambda x: f"{x.year}-{x.month:02d}-{x.day:02d} {x.hour:02d}:00:00",
        "minute": lambda x: f"{x.year}-{x.month:02d}-{x.day:02d} {x.hour:02d}:{x.minute:02d}:00",
        "second": lambda x: f"{x.year}-{x.month:02d}-{x.day:02d} {x.hour:02d}:{x.minute:02d}:{x.second:02d}",
    }
    output_col = output_col or date_col
    df[output_col] = pd.to_datetime(df[date_col]).apply(mapping[truncate_to])
    return df

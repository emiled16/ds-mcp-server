from typing import Literal

import numpy as np
import pandas as pd

from src.data_science.ds_core.atomic_functions.pandas.cast_types import AtomicTransformationError


def cyclical_time_transform(
    df: pd.DataFrame,
    datetime_column: str,
    granularity: Literal["week", "month", "quarter"],
) -> pd.DataFrame:
    """
    Transform datetime column into cyclical features using sine and cosine transformations.
    This helps capture the cyclical nature of time features.

    Args:
        df: The dataframe containing the datetime column.
        datetime_column: Name of the datetime column to transform.
        granularity: Time granularity to transform. Must be one of:
            'week': 52-week cycle
            'month': 12-month cycle
            'quarter': 4-quarter cycle

    Returns:
        pd.DataFrame: DataFrame with added cyclical time features.

    Example:
        >>> df = pd.DataFrame({'date': pd.date_range('2023-01-01', periods=5)})
        >>> cyclical_time_transform(df, 'date', 'month')
           date                 date_month_sin  date_month_cos
        0  2023-01-01          0.000          1.000
        1  2023-01-02          0.000          1.000
        2  2023-01-03          0.000          1.000
        3  2023-01-04          0.000          1.000
        4  2023-01-05          0.000          1.000
    """
    df_transformed = df.copy()

    # Ensure datetime column is datetime type
    try:
        df_transformed[datetime_column] = pd.to_datetime(df_transformed[datetime_column])
    except ValueError as e:
        raise AtomicTransformationError(f"Column {datetime_column} must be datetime type") from e

    max_values = {
        "week": 52,  # weeks in year
        "month": 12,  # months in year
        "quarter": 4,  # quarters in year
    }

    extract_funcs = {
        "week": lambda x: x.week,
        "month": lambda x: x.month,
        "quarter": lambda x: x.quarter,
    }

    max_val = max_values[granularity]
    values = df_transformed[datetime_column].apply(extract_funcs[granularity])

    # Convert to radians and calculate sine and cosine
    radians = 2 * np.pi * values / max_val

    df_transformed[f"{datetime_column}_{granularity}_sin"] = np.sin(radians)
    df_transformed[f"{datetime_column}_{granularity}_cos"] = np.cos(radians)

    return df_transformed

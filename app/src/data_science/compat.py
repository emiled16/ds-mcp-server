"""Compatibility layer after Snowflake removal. Use pandas-only types."""

import pandas as pd

# Type alias for code that used Union[pd.DataFrame, SnowparkDataFrame]
SnowparkDataFrame = pd.DataFrame

__all__ = ["SnowparkDataFrame"]

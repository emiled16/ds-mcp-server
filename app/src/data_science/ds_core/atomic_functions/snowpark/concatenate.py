from functools import reduce

from src.data_science.ds_core.utils.data_operations import find_common_columns
from src.data_science.snowflake_optional import SnowparkDataFrame, require_snowflake


def concatenate(**dfs: SnowparkDataFrame) -> SnowparkDataFrame:
    """
    Concatenate multiple dataframes.
    Args:
        dfs: The dataframes to concatenate.
    Returns:
        The concatenated dataframe.
    """
    require_snowflake()
    return reduce(
        lambda x, y: x.join(y, how="outer", on=find_common_columns([list(x.columns), list(y.columns)])),
        dfs.values(),
    )

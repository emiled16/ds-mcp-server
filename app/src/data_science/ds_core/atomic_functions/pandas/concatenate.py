from functools import reduce

import pandas as pd

from src.data_science.ds_core.utils.data_operations import find_common_columns


def concatenate(**dfs: pd.DataFrame) -> pd.DataFrame:
    """
    Concatenate multiple dataframes.
    Args:
        dfs: The dataframes to concatenate.
    Returns:
        The concatenated dataframe.
    """
    return reduce(
        lambda x, y: x.merge(
            y,
            how="outer",
            on=find_common_columns([list(x.columns), list(y.columns)]),
        ),
        dfs.values(),
    )

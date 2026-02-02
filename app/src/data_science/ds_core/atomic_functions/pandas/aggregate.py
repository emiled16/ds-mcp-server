from typing import Union

import pandas as pd


def aggregate(
    df: pd.DataFrame,
    dimensions: list[str],
    aggregations: list[Union[tuple[str, str, str], tuple[str, str]]],
) -> pd.DataFrame:
    """
    Aggregate a dataframe by dimensions and aggregations.
    If dimensions are empty, perform a global aggregation.
    Args:
        df: The dataframe to aggregate.
        dimensions: List of columns to group by.
        aggregations: List of tuples (column, aggregation function, new column name).
        If new column name is not provided, it will be the same as the column name.
        Example:
        df = pd.DataFrame({'A': [1, 2, 3, 4, 5], 'B': [10, 20, 30, 40, 50]})
        dimensions = ['A']
        aggregations = [('B', 'sum', 'B_sum')]
        aggregate(df, dimensions, aggregations)
        # Output:
        #   A  B_sum
        # 0  1      10
        # 1  2      20
        # 2  3      30
        # 3  4      40
        # 4  5      50
    Returns:
        The aggregated dataframe.
    """
    named_agg_args_len = 3  # (column, aggregation function, new column name)
    unnamed_agg_args_len = 2  # (column, aggregation function)
    # create aggregation:
    named_aggregations = {}
    for agg in aggregations:
        if len(agg) == named_agg_args_len:
            named_aggregations[agg[2]] = pd.NamedAgg(column=agg[0], aggfunc=agg[1])
        elif len(agg) == unnamed_agg_args_len:
            named_aggregations[f"{agg[1]}_{agg[0]}"] = pd.NamedAgg(column=agg[0], aggfunc=agg[1])
        else:
            raise ValueError(f"Invalid aggregation: {agg}")

    if len(dimensions) == 0:
        return df.agg(**named_aggregations).reset_index()
    return df.groupby(dimensions).agg(**named_aggregations).reset_index()

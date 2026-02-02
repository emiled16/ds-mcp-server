from typing import Union

import snowflake.snowpark.functions as f
from snowflake.snowpark import DataFrame as SnowparkDataFrame


def aggregate(
    df: SnowparkDataFrame,
    dimensions: list[str],
    aggregations: list[Union[tuple[str, str, str], tuple[str, str]]],
) -> SnowparkDataFrame:
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


    Note:
        The aggregation function must be a valid Snowflake aggregation function.
    """
    agg_list = []
    named_agg_args_len = 3  # (column, aggregation function, new column name)
    unnamed_agg_args_len = 2  # (column, aggregation function)
    for agg in aggregations:
        operation = getattr(f, agg[1])
        if len(agg) == named_agg_args_len:
            agg_list.append(operation(agg[0]).alias(agg[2]))
        elif len(agg) == unnamed_agg_args_len:
            agg_list.append(operation(agg[0]).alias(f"{agg[1]}_{agg[0]}"))
        else:
            raise ValueError(f"Invalid aggregation: {agg}")

    if len(dimensions) != 0:
        df = df.group_by(dimensions)

    return df.agg(*agg_list)

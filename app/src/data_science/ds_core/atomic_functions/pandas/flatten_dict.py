import json

import pandas as pd


def flatten_dict(
    df: pd.DataFrame,
    column: str,
    drop_raw_col: bool = False,
) -> pd.DataFrame:
    """
    Flatten a column containing dictionaries into separate columns.

    Args:
        df: The dataframe containing the dictionary column to flatten.
        column: Column name containing dictionaries to flatten.
        drop_raw_col: Whether to drop the original column after flattening. Default is False.

    Returns:
        pd.DataFrame: DataFrame with flattened dictionary columns added. Each key in the dictionary
            becomes a new column with prefix {column}_. If drop_raw_col is True, the original column
            is dropped.

    Example:
        df = pd.DataFrame({
            'id': [1, 2],
            'data': [{'a': 1, 'b': 2}, {'a': 3, 'b': 4}]
        })
        flatten_dict(df, 'data')
        # Output:
        #    id  data                 data_a  data_b
        # 0   1  {'a': 1, 'b': 2}     1       2
        # 1   2  {'a': 3, 'b': 4}     3       4
    """
    df_flattened = df.copy()

    # # Convert column to dict if it contains string representations
    # if df_flattened[column].dtype == "object":
    #     df_flattened[column] = df_flattened[column].apply(lambda x: eval(x) if isinstance(x, str) else x)

    # Flatten the dictionary column: deserialize the string to dict then flatten
    flattened = pd.json_normalize(df_flattened[column].apply(lambda x: json.loads(x)))

    # Rename columns to include original column name as prefix
    flattened.columns = [f"{column}.{col}" for col in flattened.columns]

    # Combine with original DataFrame
    df_flattened = pd.concat([df_flattened, flattened], axis=1)

    if drop_raw_col:
        df_flattened = df_flattened.drop(columns=[column])

    return df_flattened

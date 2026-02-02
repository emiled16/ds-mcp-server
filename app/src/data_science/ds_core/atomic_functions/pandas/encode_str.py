import pandas as pd
from sklearn.preprocessing import OneHotEncoder


def encode_one_hot(
    df: pd.DataFrame,
    column: str,
    drop_raw_col: bool = False,
    threshold: float = 0.01,
) -> tuple[pd.DataFrame, OneHotEncoder]:
    """
    Perform one-hot encoding on a specified categorical column using scikit-learn's OneHotEncoder.

    Args:
        df: The dataframe containing the column to encode.
        column: Column name to one-hot encode.
        drop_raw_col: Whether to drop the original column after encoding. Default is False.
        threshold: Minimum frequency threshold (between 0 and 1) for a label to remain ungrouped.
            Labels with frequency below threshold are grouped into 'other'. Default is 0.01 (1%).

    Returns:
        pd.DataFrame: DataFrame with one-hot encoded columns added. Each unique value in the original column
            becomes a new binary column with prefix {column}_. If drop_raw_col is True, the original column
            is dropped.
    """
    df_encoded = df.copy()

    # dropna to exclude NaN values from the encoding
    df_encoded[column] = df_encoded[column].dropna()

    # Initialize and fit the encoder
    encoder = OneHotEncoder(min_frequency=threshold, sparse_output=False, handle_unknown="ignore")
    encoded_data = encoder.fit_transform(df_encoded[[column]])

    # Get feature names and create encoded DataFrame
    encoded_df = pd.DataFrame(encoded_data, columns=encoder.get_feature_names_out(), index=df_encoded.index)

    # Combine with original DataFrame
    df_encoded = pd.concat([df_encoded, encoded_df], axis=1)
    if drop_raw_col:
        df_encoded = df_encoded.drop(columns=[column])

    return df_encoded, encoder

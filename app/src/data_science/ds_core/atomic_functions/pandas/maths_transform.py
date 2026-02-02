from typing import Literal

import numpy as np
import pandas as pd
from sklearn.preprocessing import PolynomialFeatures


def maths_transform(
    df: pd.DataFrame,
    columns: list[str],
    transform: Literal["square", "cube", "sqrt", "log", "inverse", "inverse_sqrt", "inverse_square"],
) -> pd.DataFrame:
    """
    Apply mathematical transformations to specified columns.

    Args:
        df: The dataframe containing columns to transform.
        columns: List of columns to apply transformation to.
        transform: Type of transformation to apply. Must be one of:
            'square': x^2
            'cube': x^3
            'sqrt': √x
            'log': ln(x)
            'inverse': 1/x
            'inverse_sqrt': 1/√x
            'inverse_square': 1/x^2

    Returns:
        pd.DataFrame: DataFrame with transformed columns.

    Example:
        >>> df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        >>> maths_transform(df, ['A', 'B'], 'square')
           A   B
        0  1  16
        1  4  25
        2  9  36
    """
    if len(columns) == 0:
        return df

    df_transformed = df.copy()

    transform_funcs = {
        "square": lambda x: np.power(x, 2),
        "cube": lambda x: np.power(x, 3),
        "sqrt": lambda x: np.sqrt(x),
        "log": lambda x: np.log(x),
        "inverse": lambda x: 1 / x,
        "inverse_sqrt": lambda x: 1 / np.sqrt(x),
        "inverse_square": lambda x: 1 / np.power(x, 2),
    }

    for col in columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            df_transformed[col + "_" + transform] = transform_funcs[transform](df[col])

    return df_transformed


def polynomial_features(
    df: pd.DataFrame,
    columns: list[str],
    degree: int = 2,
    include_bias: bool = True,
    interaction_only: bool = False,
) -> pd.DataFrame:
    """
    Generate polynomial features from specified columns.

    Args:
        df: The dataframe containing columns to transform.
        columns: List of columns to generate polynomial features from.
        degree: The maximum degree of polynomial features. Default is 2.
        include_bias: Whether to include a bias column (column of 1's). Default is True.
        interaction_only: If True, only interaction features are produced, no powers. Default is False.

    Returns:
        pd.DataFrame: DataFrame with original and polynomial feature columns.

    Example:
        >>> df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
        >>> polynomial_features(df, ['A', 'B'], degree=2)
           A  B  A^2  A*B  B^2
        0  1  4   1    4   16
        1  2  5   4   10   25
        2  3  6   9   18   36
    """
    if len(columns) == 0:
        return df

    # Filter numeric columns
    numeric_cols = [col for col in columns if pd.api.types.is_numeric_dtype(df[col])]

    if not numeric_cols:
        return df
    # Use sklearn's PolynomialFeatures

    # Create and fit polynomial features transformer
    transformer = PolynomialFeatures(degree=degree, interaction_only=interaction_only, include_bias=include_bias)
    transformer.set_output(transform="pandas")

    # Transform features
    poly_features = transformer.fit_transform(df[numeric_cols])
    poly_features = poly_features.drop(numeric_cols, axis=1)  # exclude original columns

    return pd.concat([df, poly_features], axis=1)

from typing import Literal, Optional

import pandas as pd
from sklearn.cluster import FeatureAgglomeration
from sklearn.decomposition import PCA

from src.data_science.ds_core.atomic_functions.pandas.cast_types import AtomicTransformationError


def pca_reduction(
    df: pd.DataFrame,
    columns: list[str],
    n_components: Optional[int] = 5,
) -> tuple[pd.DataFrame, PCA]:
    """
    Perform PCA dimensionality reduction on specified numeric columns.

    Args:
        df: The dataframe containing columns to transform.
        columns: List of columns to perform PCA on. Only numeric columns will be used.
        n_components: Number of components to keep. If None, keep all components.
            Defaults to 5.

    Returns:
        tuple[pd.DataFrame, PCA | None]: Tuple containing:
            - DataFrame with original columns and PCA components added with '_pca' suffix
            - Fitted PCA object, or None if no numeric columns were transformed

    Example:
        >>> df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6], 'C': ['x', 'y', 'z']})
        >>> df_pca, pca = pca_reduction(df, ['A', 'B'], n_components=1)
        >>> df_pca
           A  B  C    PCA_1
        0  1  4  x -2.121320
        1  2  5  y  0.000000
        2  3  6  z  2.121320
    """
    if len(columns) == 0:
        return df, None

    # Filter numeric columns
    numeric_cols = [col for col in columns if pd.api.types.is_numeric_dtype(df[col])]

    if not numeric_cols:
        return df, None

    # Initialize PCA
    transformer = PCA(n_components=n_components)
    transformer.set_output(transform="pandas")

    # Fit and transform the data
    df_pca = transformer.fit_transform(df[numeric_cols])

    # Rename columns to PC1, PC2, etc.
    df_pca.columns = [f"PCA_{i + 1}" for i in range(df_pca.shape[1])]

    # Combine with original dataframe
    return pd.concat([df, df_pca], axis=1), transformer


def feature_agglomeration(
    df: pd.DataFrame,
    columns: list[str],
    n_clusters: int = 2,
    metric: Literal["euclidean"] = "euclidean",
) -> tuple[pd.DataFrame, FeatureAgglomeration]:
    """
    Perform feature agglomeration on specified numeric columns to reduce dimensionality.

    Args:
        df: The dataframe containing columns to transform.
        columns: List of columns to perform agglomeration on. Only numeric columns will be used.
        n_clusters: Number of clusters to find. Defaults to 2.
        metric: Metric used to compute the linkage. Can be "euclidean" only.
            Defaults to "euclidean".

    Returns:
        tuple[pd.DataFrame, FeatureAgglomeration | None]: Tuple containing:
            - DataFrame with original columns and agglomerated features added with 'Agglomerated_Feature_' prefix
            - Fitted FeatureAgglomeration object, or None if no numeric columns were transformed

    Example:
        >>> df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6], 'C': ['x', 'y', 'z']})
        >>> df_agg, agg = feature_agglomeration(df, ['A', 'B'], n_clusters=1)
        >>> df_agg
           A  B  C  Agglomerated_Feature_1
        0  1  4  x      -1.224745
        1  2  5  y       0.000000
        2  3  6  z       1.224745
    """
    if len(columns) == 0:
        return df, None

    if n_clusters >= len(columns):
        raise AtomicTransformationError("n_clusters must be less than the number of columns")

    # Filter numeric columns
    numeric_cols = [col for col in columns if pd.api.types.is_numeric_dtype(df[col])]

    if not numeric_cols:
        return df, None

    # Initialize FeatureAgglomeration
    transformer = FeatureAgglomeration(n_clusters=n_clusters, metric=metric, linkage="ward")
    transformer.set_output(transform="pandas")

    # Fit and transform the data
    df_agg = transformer.fit_transform(df[numeric_cols])

    # Rename columns
    df_agg.columns = [f"Agglomerated_Feature_{i + 1}" for i in range(df_agg.shape[1])]

    # Combine with original dataframe
    return pd.concat([df, df_agg], axis=1), transformer

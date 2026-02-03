import ast
from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.ds_core.definitions.orchestration.transformation import BaseParameter, BaseTransformation


class FlattenListParameters(BaseParameter):
    column: str = Field(
        description="Column containing lists to flatten",
        default="",
    )
    threshold: float = Field(
        description="Minimum frequency threshold for values",
        default=0.01,
    )
    drop_raw_col: bool = Field(
        description="Whether to drop the original column after flattening",
        default=False,
    )
    vocabulary: list[str] = Field(
        description="List of reference values to keep",
        default=[],
    )


class FlattenList(BaseTransformation):
    name: Literal["FlattenList"] = "FlattenList"
    display_name: str = "Flatten List"
    description: str = """
        Flatten a column containing lists into a string with elements separated by the specified separator.
        The new column has the same name with "_flattened" suffix.
        If drop_raw_col is True, the original column is dropped.
    """
    parameters: FlattenListParameters

    @classmethod
    def parse_list(cls, input_string: str) -> list[str]:
        # If it looks like a Python list literal (starts with '['), try ast.literal_eval
        if input_string.startswith("["):
            try:
                return list(ast.literal_eval(input_string))
            except (ValueError, SyntaxError):
                pass
        # Simple comma-separated string
        return [item.strip() for item in input_string.split(",")]

    def _validate(self, df: pd.DataFrame) -> "FlattenList":
        if self.parameters.column not in df.columns:
            raise ValueError(f"Column {self.parameters.column} not found in dataframe")
        return self

    def _fit_pandas(self, df: pd.DataFrame) -> "FlattenList":
        """Fit the transformer by learning the vocabulary from the input data.

        Args:
            df: Input DataFrame containing the list column to analyze

        Returns:
            self: Returns the instance itself
        """
        self._validate(df)
        df_fitted = df.copy()
        df_fitted[self.parameters.column] = df_fitted[self.parameters.column].dropna()

        # Convert strings to lists if needed (deserialization)
        series_items_deserialized: pd.Series = df_fitted[self.parameters.column].apply(
            lambda x: FlattenList.parse_list(x) if isinstance(x, str) else x,
        )

        # Get all unique values and their frequencies
        frequency_series = series_items_deserialized.explode().value_counts(normalize=True)
        self.parameters.vocabulary = frequency_series[frequency_series >= self.parameters.threshold].index.tolist()

        return self

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        self._validate(df)
        df_transformed = df.copy()

        # Convert strings to lists if needed
        df_transformed["deserialized_column"] = df_transformed[self.parameters.column].apply(
            lambda x: FlattenList.parse_list(x) if isinstance(x, str) else x,
        )

        # Create one-hot encoded columns for each value in vocabulary
        for value in self.parameters.vocabulary:
            col_name = f"{self.parameters.column}_{value}"
            df_transformed[col_name] = df_transformed["deserialized_column"].apply(
                lambda x: 1 if isinstance(x, (list, tuple)) and value in x else 0,
            )

        # Drop original column if specified
        if self.parameters.drop_raw_col:
            df_transformed = df_transformed.drop(columns=[self.parameters.column])
        df_transformed = df_transformed.drop(columns=["deserialized_column"])

        return df_transformed

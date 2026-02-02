from typing import Any, ClassVar, Dict, Optional, Union

import pandas as pd
from pydantic import BaseModel, model_validator
from sklearn.preprocessing import StandardScaler

from src.data_science.ds_core.atomic_functions import AtomicTransformer

from ..dataset import Dataset


class DataCleaner(AtomicTransformer):
    dataset: Dataset

    NA_DICT: ClassVar[Dict[Optional[str], Any]] = {
        None: pd.NA,  # Python None
        "": pd.NA,  # Empty string
        " ": pd.NA,  # Single space
        "nan": pd.NA,  # String NaN
        "NaN": pd.NA,  # String NaN (different case)
        "NA": pd.NA,  # String NA
        "null": pd.NA,  # String null
        "NULL": pd.NA,  # String NULL
        "None": pd.NA,  # String None
        "NONE": pd.NA,  # String NONE
    }

    # Pydantic Config
    class Config:
        arbitrary_types_allowed = True

    # Pydantic Validator
    @model_validator(mode="after")
    def validate_dataset(self) -> "DataCleaner":
        if not isinstance(self.dataset, Dataset):
            raise ValueError("dataset must be a Dataset")
        return self

    # Data Cleaning Functions
    def column_select(self, columns: list[str], *, inplace: bool = False) -> Optional[pd.DataFrame]:
        if inplace:
            self.dataset.set_df(self.dataset.df[columns])
            return None
        return self.dataset.df[columns]

    def column_rename(self, columns: dict[str, str], *, inplace: bool = False) -> Optional[pd.DataFrame]:
        if inplace:
            self.dataset.set_df(self.dataset.df.rename(columns=columns))
            return None
        return self.dataset.df.rename(columns=columns)

    def column_drop(self, columns: list[str], *, inplace: bool = False) -> Optional[pd.DataFrame]:
        if inplace:
            self.dataset.set_df(self.dataset.df.drop(columns, axis=1))
            return None
        return self.dataset.df.drop(columns, axis=1)

    def filter_rows(
        self,
        column: str,
        operator: str,
        value: Union[str, float, bool],
        *,
        inplace: bool = False,
    ) -> Optional[pd.DataFrame]:
        # Apply filter based on operator type
        match operator:
            case ">":
                mask = self.dataset.df[column] > value
            case "<":
                mask = self.dataset.df[column] < value
            case ">=":
                mask = self.dataset.df[column] >= value
            case "<=":
                mask = self.dataset.df[column] <= value
            case "==":
                mask = self.dataset.df[column] == value
            case "!=":
                mask = self.df[column] != value
            case "in":
                mask = self.dataset.df[column].isin(value)
            case "not in":
                mask = ~self.dataset.df[column].isin(value)
            case "like":
                mask = self.dataset.df[column].str.contains(value, na=False)
            case "not like":
                mask = ~self.dataset.df[column].str.contains(value, na=False)
            case _:
                raise ValueError(f"Unsupported operator: {operator}")

        if inplace:
            self.dataset.set_df(self.dataset.df[mask])
            return None
        return self.dataset.df[mask]

    def type_cast(self, columns: dict[str, type]) -> None:
        for column, new_type in columns.items():
            if new_type is str:
                # Handle None or mixed types explicitly for object-to-str conversion
                self.dataset.df[column] = self.dataset.df[column].apply(lambda x: "" if x is None else str(x))
            elif new_type == "datetime":
                self.dataset.df[column] = pd.to_datetime(self.dataset.df[column])
            else:
                self.dataset.df[column] = self.dataset.df[column].astype(new_type)

    def drop_0_variance(self, *, inplace: bool = False) -> Optional[pd.DataFrame]:
        # Find columns with only one unique value (0 variance)
        zero_var_cols = [col for col in self.dataset.df.columns if len(self.dataset.df[col].value_counts()) <= 1]
        # Filter to only include columns that actually exist in the DataFrame
        zero_var_cols = [col for col in zero_var_cols if col in self.dataset.df.columns]

        if not zero_var_cols:  # If no zero variance columns found
            return self.dataset.df

        if inplace:
            self.dataset.set_df(self.dataset.df.drop(columns=zero_var_cols))
            return self.dataset.df

        return self.dataset.df.drop(columns=zero_var_cols)

    def drop_duplicates(self, columns: Optional[list[str]] = None, *, inplace: bool = False) -> Optional[pd.DataFrame]:
        if inplace:
            if columns:
                self.dataset.set_df(self.dataset.df.drop_duplicates(subset=columns))
            self.dataset.set_df(self.dataset.df.drop_duplicates())
            return None
        if columns:
            return self.dataset.df.drop_duplicates(subset=columns)
        return self.dataset.df.drop_duplicates()

    def drop_nulls(self, *, column: Optional[str] = None, inplace: bool = False) -> Optional[pd.DataFrame]:
        # Replace common NA values with pandas NA
        df_cleaned = self.get_df().replace(self.NA_DICT)
        df_cleaned = df_cleaned.dropna(subset=[column]) if column else df_cleaned.dropna()
        if inplace:
            self.dataset.set_df(df_cleaned)
            return None
        return df_cleaned

    def handle_nulls(self, column: str, method: str) -> None:
        self.dataset.set_df(self.dataset.df.replace(self.NA_DICT))
        match method:
            case "mean":
                self.dataset.df[column] = self.dataset.df[column].fillna(self.dataset.df[column].mean())
            case "median":
                self.dataset.df[column] = self.dataset.df[column].fillna(self.dataset.df[column].median())
            case "mode":
                self.dataset.df[column] = self.dataset.df[column].fillna(self.dataset.df[column].mode()[0])

    def _calculate_iqr(self, column: str) -> float:
        q1 = self.dataset.df[column].quantile(0.25)
        q3 = self.dataset.df[column].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        return lower, upper

    def calculate_outlier_ratios(self, id_column: str) -> pd.DataFrame:
        # Get numeric columns only
        numeric_cols = self.dataset.df.select_dtypes(include=["number"]).columns.tolist()
        numeric_cols = [col for col in numeric_cols if col != id_column]

        if numeric_cols:
            # Calculate outlier flags for each numeric column
            outlier_flags = pd.DataFrame()
            outlier_flags[id_column] = self.dataset.df[id_column]

            for col in numeric_cols:
                lower, upper = self._calculate_iqr(col)
                # Flag if value is outside bounds
                outlier_flags[f"{col}_outlier"] = (
                    (self.dataset.df[col] < lower) | (self.dataset.df[col] > upper)
                ).astype(int)

            # Calculate ratio of columns where each ID is an outlier
            outlier_cols = [col for col in outlier_flags.columns if col.endswith("_outlier")]
            outlier_summary = outlier_flags.groupby(id_column)[outlier_cols].sum()
            outlier_summary["outlier_ratio"] = outlier_summary.mean(axis=1)
            outlier_summary["num_outlier_cols"] = outlier_summary[outlier_cols].sum(axis=1)

            # Sort and display results
            results_df = outlier_summary[["outlier_ratio", "num_outlier_cols"]].sort_values(
                "outlier_ratio", ascending=False
            )
            results_df["outlier_ratio"] = results_df["outlier_ratio"].round(3)
        return results_df

    def drop_outliers(
        self,
        lower_bound: Optional[float] = None,
        upper_bound: Optional[float] = None,
        filter_column: Optional[str] = None,
        id_column: Optional[str] = None,
        ids: Optional[list[str]] = None,
    ) -> None:
        # By Ratio
        if id_column:
            if ids:
                self.dataset.set_df(self.dataset.df[~self.dataset.df[id_column].isin(ids)])
        # By Column
        else:
            if filter_column:
                mask = pd.Series(True, index=self.df.index)
            if lower_bound is not None:
                mask &= self.dataset.df[filter_column] >= lower_bound
            if upper_bound is not None:
                mask &= self.dataset.df[filter_column] <= upper_bound
            self.dataset.set_df(self.dataset.df[mask])

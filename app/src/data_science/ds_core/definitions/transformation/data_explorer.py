from typing import Any, Dict, Final, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
from pydantic import BaseModel, model_validator
from scipy.stats import boxcox
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from ..dataset import Dataset


class DataExplorer(BaseModel):
    dataset: Dataset

    class Config:
        arbitrary_types_allowed = True

    @model_validator(mode="after")
    def validate_dataset(self) -> "DataExplorer":
        if not isinstance(self.dataset, Dataset):
            raise ValueError("dataset must be a Dataset")
        return self

    # EDA Functions
    ## Layer 1: Basic Functions
    def get_shape_info(self) -> pd.DataFrame:
        df = self.dataset.get_df()
        rows, cols = df.shape
        na_dict = self.__calculate_na()
        self._shape_df = pd.DataFrame(
            {
                "Shape Info": [rows, cols, na_dict["complete_rows"], na_dict["complete_percentage"]],
            },
            index=["Row Count", "Column Count", "Number of Filled Rows", "Filled Rows %"],
        )

        return self._shape_df

    def get_dtype_distribution(self) -> pd.DataFrame:
        # Get dtype counts
        df = self.dataset.get_df()
        dtype_counts = df.dtypes.value_counts()

        # Create DataFrame with dtype info
        return pd.DataFrame(
            {
                "Data Type": dtype_counts.index.astype(str),
                "Column Count": dtype_counts.to_numpy(),
            }
        )

    def get_column_types(self) -> pd.DataFrame:
        df = self.dataset.get_df()
        return pd.DataFrame(
            {
                "Column Name": df.columns,
                "Data Type": df.dtypes.astype(str),
            }
        ).reset_index(drop=True)

    def get_na_rank(self) -> pd.DataFrame:
        df = self.dataset.get_df()
        total_rows = len(df)
        missing_mask = (
            df.isna()  # Catches np.nan, pd.NA
            | df.isnull()  # Catches None, np.nan
            | df.eq("")  # Empty strings
            | df.eq("null")  # String 'null'
            | df.eq("NULL")  # String 'NULL'
            | df.eq("NaN")  # String 'NaN'
            | df.eq("na")  # String 'na'
            | df.eq("NA")  # String 'NA'
            | df.eq(" ")  # Single space
        )

        # Count NAs for each column
        na_counts = missing_mask.sum()
        na_percentages = (na_counts / total_rows) * 100

        # Create DataFrame and sort
        self._na_rank_df = pd.DataFrame(
            {
                "Column Name": df.columns,
                "NA %": na_percentages.round(2),
            }
        ).sort_values("NA %", ascending=False)

        return self._na_rank_df

    # Private Methods
    def __calculate_na(self) -> Dict[str, Any]:
        df = self.dataset.get_df()
        total_rows = len(df)
        missing_patterns = [
            df.isna(),  # Catches np.nan, pd.NA
            df.isnull(),  # Catches None, np.nan
            df.eq(""),  # Empty strings
            df.eq("null"),  # String 'null'
            df.eq("NULL"),  # String 'NULL'
            df.eq("NaN"),  # String 'NaN'
            df.eq("na"),  # String 'na'
            df.eq("NA"),  # String 'NA'
            df.eq(" "),  # Single space
        ]

        # Combine all missing patterns
        combined_missing = pd.concat(missing_patterns, axis=1).any(axis=1)

        # Calculate percentage of complete rows
        rows_with_na = combined_missing.sum()
        complete_rows = total_rows - rows_with_na
        complete_percentage = round((complete_rows / total_rows) * 100, 2)

        return {
            "complete_rows": complete_rows,
            "complete_percentage": round(complete_percentage, 2),
        }

    ## Layer 2: Target Analysis
    def prepare_graph_data(
        self,
        x_col: str,
        y_col: str,
        group_cols: list[str] | None = None,
        filter_conditions: list[dict] | None = None,
        agg_func: str | None = None,
    ) -> pd.DataFrame:
        """
        Prepare data for graphing by applying filtering, grouping, and aggregation.

        Args:
            x_col: Column to use for x-axis
            y_col: Column to use for y-axis (target)
            group_cols: Optional columns to group by
            filter_conditions: List of dicts with 'column', 'operator', and 'value' keys
            agg_func: Optional aggregation function ('mean', 'median', etc.)
        """
        df = self.dataset.get_df().copy()

        # Apply filters if any
        if filter_conditions:
            df = self.analyze_filter_conditions(filter_conditions)

        # Continue with existing grouping and aggregation logic...
        if group_cols and agg_func:
            group_by_cols = list(set([x_col] + group_cols))
            agg_cols = [y_col]
            agg_dict = {col: agg_func for col in agg_cols}
            df = df.groupby(group_by_cols).agg(agg_dict).reset_index()

        return df

    def analyze_filter_conditions(self, filter_conditions: list[dict]) -> pd.DataFrame:
        df = self.dataset.get_df().copy()
        for condition in filter_conditions:
            col = condition["column"]
            op = condition["operator"]
            val = condition["value"]

            match op:
                case ">":
                    df = df[df[col] > val]
                case ">=":
                    df = df[df[col] >= val]
                case "<":
                    df = df[df[col] < val]
                case "<=":
                    df = df[df[col] <= val]
                case "==":
                    df = df[df[col] == val]
                case "!=":
                    df = df[df[col] != val]
                case "in":
                    df = df[df[col].isin(val)]
                case "not in":
                    df = df[~df[col].isin(val)]
                case "like":
                    df = df[df[col].str.contains(val.replace("%", ".*"), regex=True)]
                case "not like":
                    df = df[~df[col].str.contains(val.replace("%", ".*"), regex=True)]

        return df

    ## Layer 3: Variable Analysis
    def calculate_correlation_scores(self, abs_val: bool = False) -> pd.DataFrame:
        df = self.dataset.get_df()
        numeric_df = df.select_dtypes(include=["number"])
        if abs_val:
            return round(numeric_df.corr().abs(), 2)
        return round(numeric_df.corr(), 2)

    def get_categorical_distribution(self, column: str | None = None) -> pd.DataFrame:
        df = self.dataset.get_df()
        bins_summary = []

        if column == "All Columns":
            # Calculate for all columns
            for col in df.select_dtypes(include=["object", "category", "number"]).columns:
                counts = df[col].value_counts()
                for value in counts.index:
                    bins_summary.append(
                        {
                            "Column": col,
                            "Value": str(value),  # Convert to string to handle mixed types
                            "Count": counts[value],
                            "Percentage": (counts[value] / len(df)) * 100,
                        }
                    )
        else:
            # Calculate for specific column
            counts = df[column].value_counts()
            for value in counts.index:
                bins_summary.append(
                    {
                        "Column": column,
                        "Value": str(value),
                        "Count": counts[value],
                        "Percentage": (counts[value] / len(df)) * 100,
                    }
                )

        return pd.DataFrame(bins_summary)

    def transform_column(self, y_column: str, transformation_type: str) -> pd.DataFrame:
        df = self.dataset.get_df().copy()
        numeric_cols = df.select_dtypes(include=["number"]).columns
        for col in numeric_cols:  # Only transform numeric columns
            if col != y_column:
                match transformation_type:
                    case "Squared":
                        df[col] = df[col] ** 2
                    case "Cubed":
                        df[col] = df[col] ** 3
                    case "Square Root":
                        df[col] = df[col] ** 0.5
                    case "Log":
                        df[col] = np.log(df[col])
                    case "Reciprocal":
                        df[col] = 1 / df[col]
                    case "Sine":
                        df[col] = np.sin(df[col])
                    case "Cos":
                        df[col] = np.cos(df[col])
        return df

    ## Layer 4: Outlier Analysis
    def _find_outliers_iqr(self, column: str) -> pd.Series:
        df = self.dataset.get_df()
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        return (df[column] < lower_bound) | (df[column] > upper_bound)

    def analyze_outliers_all_columns(self, primary_key_col: str) -> pd.DataFrame:
        """
        Analyze outliers across all numeric columns.
        Based on primary key column, find the rows which are outliers across the most amount of rows.
        The idea is that observations which are outliers across the highest number of dimensions are
        the ones which are most likely to be anomalous. I.E. if an observation is an outlier in
        7/8 potential columns, it is most likely anomalous to the dataset as a whole.
        Args:
            primary_key_col: Column to group results by

        Returns:
            DataFrame with outlier counts per primary key (ranked descending)
        """
        df = self.dataset.get_df()
        numerical_columns = df.select_dtypes(include=["number"]).columns
        num_cols = len(numerical_columns)

        # Find outliers for each numeric column
        outliers_list = []
        for col in numerical_columns:
            outliers_list.append(self._find_outliers_iqr(col))

        # Combine all outlier results
        outliers_df = pd.concat(outliers_list, axis=1)
        outliers_df.columns = numerical_columns
        outliers_df["outlier_count"] = outliers_df.sum(axis=1)

        # Filter and prepare results
        filtered_df = df[outliers_df["outlier_count"] > 1].copy()
        filtered_df["outlier_count"] = outliers_df["outlier_count"]

        # Group by primary key
        grouped = filtered_df.groupby(primary_key_col).agg(
            outlier_count=("outlier_count", "sum"),
        )
        grouped["outlier_ratio"] = (grouped["outlier_count"] / num_cols).round(2)

        return grouped.sort_values("outlier_ratio", ascending=False).reset_index()

    ## Layer 5: Transformation Analysis
    def calculate_pca(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        # Get numeric columns and handle missing values
        df = self.dataset.get_df()
        numeric_df = df.select_dtypes(include=["number"])
        if numeric_df.empty:
            raise ValueError("No numeric columns available for PCA")

        # Remove rows with NA values
        numeric_df = numeric_df.dropna()
        if numeric_df.empty:
            raise ValueError("No complete rows available for PCA after removing NA values")

        try:
            # Scale the data
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(numeric_df)

            # Perform PCA
            pca = PCA()
            pca.fit(scaled_data)

        except Exception as e:
            raise ValueError(f"Error performing PCA: {str(e)}")

        return self.process_pca(pca, numeric_df)

    def process_pca(self, pca: PCA, numeric_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        # Create results DataFrame
        pca_df = pd.DataFrame(
            {
                "Principal Component": [f"PC{i+1}" for i in range(len(pca.explained_variance_ratio_))],
                "Explained Variance Ratio": pca.explained_variance_ratio_,
                "Cumulative Explained Variance": pca.explained_variance_ratio_.cumsum(),
                "Eigenvalue": pca.explained_variance_,
            },
            index=[f"PC{i+1}" for i in range(len(pca.explained_variance_ratio_))],
        )

        # Create components DataFrame and sort by explained variance
        pca_components = pd.DataFrame(pca.components_, columns=numeric_df.columns)
        sorted_indices = (
            pca_df["Explained Variance Ratio"].sort_values(ascending=False).index.str.replace("PC", "").astype(int) - 1
        )
        pca_components = pca_components.iloc[sorted_indices].T

        # Rename columns to start at 1 instead of 0
        pca_components.columns = [f"PC{i+1}" for i in range(len(pca_components.columns))]

        return pca_df, pca_components

    def compute_and_show_box_cox(self) -> pd.DataFrame:
        # Box-Cox transformation threshold constants
        LAMBDA_THRESHOLD: Final[float] = 0.01
        SQRT_THRESHOLD: Final[float] = 0.5
        NO_TRANSFORM_THRESHOLD: Final[float] = 1.0
        SQUARE_THRESHOLD: Final[float] = 2.0

        df = self.dataset.get_df()
        numeric_df = df.select_dtypes(include=["number"])
        box_cox_results = {
            "Variable": [],
            "Box-Cox Lambda": [],
            "Transformation Type": [],
            "Transformation Details": [],
        }

        for col in numeric_df.columns:
            col_data = numeric_df[col].dropna()

            if col_data.empty:
                continue

            # Check for negative or zero values
            if (col_data <= 0).any():
                shift_value = abs(col_data.min()) + 1
                shifted_data = col_data + shift_value
            else:
                shifted_data = col_data

            try:
                # Apply Box-Cox transformation
                _, lambda_value = boxcox(shifted_data)

                # Determine transformation recommendation
                if abs(lambda_value) < LAMBDA_THRESHOLD:
                    transformation_type = "Log transformation"
                    transformation_details = "Log(x)"
                elif abs(lambda_value - SQRT_THRESHOLD) < LAMBDA_THRESHOLD:
                    transformation_type = "Square root transformation"
                    transformation_details = "x^(1/2)"
                elif abs(lambda_value - NO_TRANSFORM_THRESHOLD) < LAMBDA_THRESHOLD:
                    transformation_type = "No transformation needed"
                    transformation_details = "x"
                elif abs(lambda_value - SQUARE_THRESHOLD) < LAMBDA_THRESHOLD:
                    transformation_type = "Square transformation"
                    transformation_details = "x^2"
                elif lambda_value < 0:
                    transformation_type = "Inverse power transformation"
                    transformation_details = f"1/x^{abs(lambda_value):.2f}"
                else:
                    transformation_type = "Power transformation"
                    transformation_details = f"x^{lambda_value:.2f}"

                box_cox_results["Variable"].append(col)
                box_cox_results["Box-Cox Lambda"].append(round(lambda_value, 4))
                box_cox_results["Transformation Type"].append(transformation_type)
                box_cox_results["Transformation Details"].append(transformation_details)

            except Exception as e:
                box_cox_results["Variable"].append(col)
                box_cox_results["Box-Cox Lambda"].append(None)
                box_cox_results["Transformation Type"].append("Error")
                box_cox_results["Transformation Details"].append(f"Could not calculate: {str(e)}")

        return pd.DataFrame(box_cox_results)

    ## Layer 6: Clustering Analysis
    def calculate_kmeans(
        self,
        x_col: str,
        y_col: str,
        n_clusters: int = 3,
        random_state: int = 42,
        init: str = "k-means++",
    ) -> Tuple[pd.DataFrame, px.scatter]:
        """
        Perform K-means clustering on specified columns.

        Args:
            x_col: Column to use for x-axis
            y_col: Column to use for y-axis
            n_clusters: Number of clusters for K-means
            random_state: Random seed for reproducibility
            init: Initialization method for k-means

        Returns:
            Tuple of (clustered DataFrame, plotly figure)
        """
        # Get data for clustering
        df = self.dataset.get_df()
        cluster_df = df[[x_col, y_col]].copy()

        # Drop NA values
        cluster_df = cluster_df.dropna()
        if cluster_df.empty:
            raise ValueError("No complete rows available for clustering after removing NA values")

        try:
            # Perform clustering
            init_method = "k-means++" if init == "k-means++" else "random"
            kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, init=init_method)
            kmeans_labels = kmeans.fit_predict(cluster_df)

            # Add cluster labels (starting from 1)
            cluster_df["Cluster"] = (kmeans_labels + 1).astype(str)

            # Sort cluster labels for consistent legend
            cluster_order = sorted(cluster_df["Cluster"].unique(), key=lambda x: int(x))

            # Create visualization
            fig = px.scatter(
                cluster_df,
                x=x_col,
                y=y_col,
                color="Cluster",
                title=f"K-means Clustering (k={n_clusters})",
                color_discrete_sequence=px.colors.qualitative.Set1,
                category_orders={"Cluster": cluster_order},
            )

            # Update layout
            fig.update_layout(
                legend_title_text="Clusters",
                legend=dict(itemsizing="constant"),
                xaxis_title=x_col,
                yaxis_title=y_col,
            )
        except Exception as e:
            raise ValueError(f"Error performing K-means clustering: {str(e)}")

        return cluster_df, fig

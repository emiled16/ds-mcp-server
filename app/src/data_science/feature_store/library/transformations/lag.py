from typing import Literal

import pandas as pd
from pydantic import Field

from src.data_science.compat import SnowparkDataFrame
from src.data_science.ds_core.atomic_functions.pandas.lag import lag as pandas_lag
from src.data_science.ds_core.atomic_functions.snowpark.lag import lag as snowpark_lag
from src.data_science.ds_core.definitions.orchestration.transformation import (
    BaseParameter,
    BaseTransformation,
)


class LagParameters(BaseParameter):
    lags: dict[str, list[int]] = Field(
        description=(
            "Lags to apply to each column, e.g. {'column_name': [1, 2]} will create two new columns "
            "with the original column name suffixed with _lag_1 and _lag_2"
        ),
        default_factory=dict,
    )
    columns_to_order_by: list[str] = Field(
        description="Columns to sort by",
        default_factory=list,
    )

    columns_to_partition_by: list[str] = Field(
        description="Columns to partition by",
        default_factory=list,
    )
    fillna: bool = Field(default=True, description="To Fill the empty lags with 0 or not")
    suffix: str | None = Field(default=None)


class Lag(BaseTransformation):
    # TODO: Add parameter to `group by` and `order by` before lagging,
    name: Literal["Lag"] = "Lag"
    display_name: str = "Create Lagged Features"
    description: str = """"
        The dataframe is first partitioned by the columns specified in `columns_to_partition_by`
        and then sorted by the columns specified in `columns_to_order_by` before lagging.
        The resulting dataframe will have the original columns plus the new lagged columns.
        Example:
        ```
        df = pd.DataFrame({
            'product_id': ['A', 'A', 'A', 'B', 'B', 'B', 'B'],
            'date': ['2021-01-01', '2021-01-02', '2021-01-03', '2021-01-01', '2021-01-02', '2021-01-03', '2021-01-04'],
            'value': [1, 2, 3, 4, 5, 6, 7]
        })
        > df:
        | product_id | date       | value |
        |------------|------------|-------|
        | A          | 2021-01-01 | 1     |
        | A          | 2021-01-02 | 2     |
        | A          | 2021-01-03 | 3     |
        | B          | 2021-01-01 | 4     |
        | B          | 2021-01-02 | 5     |
        | B          | 2021-01-03 | 6     |
        | B          | 2021-01-04 | 7     |

        result = (
            Lag(
                lags={"value": [1, 2]},
                columns_to_order_by=["date"],
                columns_to_partition_by=["product_id"],
            )
            .fit_transform(df)
        )
        > result:
        | product_id | date       | value | value_lag_1 | value_lag_2 |
        |------------|------------|-------|-------------|-------------|
        | A          | 2021-01-01 | 1     | null        | null        |
        | A          | 2021-01-02 | 2     | 1           | null        |
        | A          | 2021-01-03 | 3     | 2           | 1           |
        | B          | 2021-01-01 | 4     | null        | null        |
        | B          | 2021-01-02 | 5     | 4           | null        |
        | B          | 2021-01-03 | 6     | 5           | 4           |
        | B          | 2021-01-04 | 7     | 6           | 5           |
        ```
        """.strip()
    parameters: LagParameters = Field(default=LagParameters())

    def _fit(self, _df: pd.DataFrame | SnowparkDataFrame) -> "Lag":
        return self

    def _fit_snowpark(self, df: SnowparkDataFrame) -> "Lag":
        return self._fit(df)

    def _fit_pandas(self, df: pd.DataFrame) -> "Lag":
        return self._fit(df)

    def _transform_pandas(self, df: pd.DataFrame) -> pd.DataFrame:
        indexes = df.index.names
        df = df.reset_index()

        new_df = pandas_lag(
            df=df.copy(deep=True),
            lags=self.parameters.lags,
            order_by=self.parameters.columns_to_order_by,
            partition_by=self.parameters.columns_to_partition_by,
            fillna=self.parameters.fillna,
            suffix=self.parameters.suffix,
        )
        return new_df.set_index(indexes)

    def _transform_snowpark(self, df: SnowparkDataFrame) -> SnowparkDataFrame:
        return snowpark_lag(
            df=df,
            lags=self.parameters.lags,
            order_by=self.parameters.columns_to_order_by,
            partition_by=self.parameters.columns_to_partition_by,
        )

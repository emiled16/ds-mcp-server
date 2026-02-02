from typing import List, Optional, Union

import pandas as pd
from pydantic import BaseModel, model_validator
from snowflake.snowpark import DataFrame as SnowparkDataFrame


# Base class for holding universal dataframe
class Dataset(BaseModel):
    df: Union[pd.DataFrame, SnowparkDataFrame]
    name: Optional[str] = None
    description: Optional[str] = None
    train_indices: Optional[List[int]] = None
    val_indices: Optional[List[int]] = None
    test_indices: Optional[List[int]] = None

    class Config:
        arbitrary_types_allowed = True

    @model_validator(mode="after")
    def validate_df(self) -> "Dataset":
        if not isinstance(self.df, (pd.DataFrame, SnowparkDataFrame)):
            raise ValueError("The 'df' field must be a pandas DataFrame or Snowpark DataFrame")
        return self

    def get_df(self) -> Union[pd.DataFrame, SnowparkDataFrame]:
        return self.df

    def set_df(self, df: Union[pd.DataFrame, SnowparkDataFrame]) -> None:
        if not isinstance(df, (pd.DataFrame, SnowparkDataFrame)):
            raise ValueError("The 'df' field must be a pandas DataFrame or Snowpark DataFrame")
        self.df = df

    def to_pandas(self) -> pd.DataFrame:
        if isinstance(self.df, SnowparkDataFrame):
            self.set_df(self.df.to_pandas())
            return self.df
        return self.df

    def to_snowpark(self) -> SnowparkDataFrame:
        # TODO: implement this
        pass

    def config_df_output(self, head_num: Optional[int] = None, tail_num: Optional[int] = None) -> pd.DataFrame:
        df = self.get_df()
        if isinstance(df, SnowparkDataFrame):
            df = df.to_pandas()
        if head_num and not tail_num:
            return df.head(head_num)
        if tail_num and not head_num:
            return df.tail(tail_num)
        if head_num and tail_num:
            return pd.concat([df.head(head_num), df.tail(tail_num)])
        return df

    def set_train_indices(self, train_indices: List[int]) -> None:
        self.train_indices = train_indices

    def set_val_indices(self, val_indices: List[int]) -> None:
        self.val_indices = val_indices

    def set_test_indices(self, test_indices: List[int]) -> None:
        self.test_indices = test_indices

    def get_train_indices(self) -> List[int]:
        return self.train_indices

    def get_val_indices(self) -> List[int]:
        return self.val_indices

    def get_test_indices(self) -> List[int]:
        return self.test_indices

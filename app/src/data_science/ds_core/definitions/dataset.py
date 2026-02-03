import pandas as pd
from pydantic import BaseModel, model_validator


# Base class for holding universal dataframe
class Dataset(BaseModel):
    df: pd.DataFrame
    name: str | None = None
    description: str | None = None
    train_indices: list[int] | None = None
    val_indices: list[int] | None = None
    test_indices: list[int] | None = None

    class Config:
        arbitrary_types_allowed = True

    @model_validator(mode="after")
    def validate_df(self) -> "Dataset":
        if not isinstance(self.df, pd.DataFrame):
            raise ValueError("The 'df' field must be a pandas DataFrame or Snowpark DataFrame")
        return self

    def get_df(self) -> pd.DataFrame:
        return self.df

    def set_df(self, df: pd.DataFrame) -> None:
        if not isinstance(df, pd.DataFrame):
            raise ValueError("The 'df' field must be a pandas DataFrame")
        self.df = df

    def to_pandas(self) -> pd.DataFrame:
        return self.df

    def config_df_output(self, head_num: int | None = None, tail_num: int | None = None) -> pd.DataFrame:
        df = self.get_df()
        if head_num and not tail_num:
            return df.head(head_num)
        if tail_num and not head_num:
            return df.tail(tail_num)
        if head_num and tail_num:
            return pd.concat([df.head(head_num), df.tail(tail_num)])
        return df

    def set_train_indices(self, train_indices: list[int]) -> None:
        self.train_indices = train_indices

    def set_val_indices(self, val_indices: list[int]) -> None:
        self.val_indices = val_indices

    def set_test_indices(self, test_indices: list[int]) -> None:
        self.test_indices = test_indices

    def get_train_indices(self) -> list[int]:
        return self.train_indices

    def get_val_indices(self) -> list[int]:
        return self.val_indices

    def get_test_indices(self) -> list[int]:
        return self.test_indices

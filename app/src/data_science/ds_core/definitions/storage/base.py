from abc import ABC, abstractmethod
from typing import Any, Literal, Union

import pandas as pd
from pydantic import BaseModel
from src.data_science.compat import SnowparkDataFrame

DataFrame = Union[pd.DataFrame, SnowparkDataFrame]


class BaseStorage(BaseModel, ABC):
    engine: Literal["snowflake", "local"]
    path: str

    @abstractmethod
    def save_dataset(self, dataset: DataFrame, table_name: str) -> None:
        pass

    @abstractmethod
    def load_dataset(self, table_name: str) -> DataFrame:
        pass

    @abstractmethod
    def save_artifact(self, artifact: Any, artifact_name: str) -> None:
        pass

    @abstractmethod
    def load_artifact(self, artifact_name: str) -> Any:
        pass

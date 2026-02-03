from abc import ABC, abstractmethod
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, Field


class BaseStorage(BaseModel, ABC):
    engine: Literal["local"] = Field(default="local")  # only local storage is supported for now
    path: str

    @abstractmethod
    def save_dataset(self, dataset: pd.DataFrame, table_name: str) -> None:
        pass

    @abstractmethod
    def load_dataset(self, table_name: str) -> pd.DataFrame:
        pass

    @abstractmethod
    def save_artifact(self, artifact: Any, artifact_name: str) -> None:
        pass

    @abstractmethod
    def load_artifact(self, artifact_name: str) -> Any:
        pass

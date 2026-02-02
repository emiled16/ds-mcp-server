from abc import ABC, abstractmethod
from typing import Union

import pandas as pd
from pydantic import BaseModel
from snowflake import snowpark


class BaseSplitter(BaseModel, ABC):
    @abstractmethod
    def split(self, dataset: Union[pd.DataFrame, snowpark.DataFrame], engine: str) -> tuple[str, str]:
        pass

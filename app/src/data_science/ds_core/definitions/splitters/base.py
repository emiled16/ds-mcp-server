from abc import ABC, abstractmethod
from typing import Any

import pandas as pd
from pydantic import BaseModel


class BaseSplitter(BaseModel, ABC):
    @abstractmethod
    def split(self, dataset: pd.DataFrame | Any, engine: str) -> tuple[str, str]:
        pass

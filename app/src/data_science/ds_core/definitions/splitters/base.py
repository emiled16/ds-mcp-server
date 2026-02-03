from abc import ABC, abstractmethod

import pandas as pd
from pydantic import BaseModel


class BaseSplitter(BaseModel, ABC):
    @abstractmethod
    def split(self, dataset: pd.DataFrame) -> tuple[str, str]:
        pass

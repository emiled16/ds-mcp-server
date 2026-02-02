import pandas as pd
from pydantic import BaseModel, model_validator

from src.data_science.ds_core.atomic_functions import AtomicTransformer

from ..dataset import Dataset


# Transformation base class
class DataTransformer(AtomicTransformer):
    dataset: Dataset

    class Config:
        arbitrary_types_allowed = True

    @model_validator(mode="after")
    def validate_dataset(self) -> "DataTransformer":
        if not isinstance(self.dataset, Dataset):
            raise ValueError("dataset must be a Dataset")
        return self

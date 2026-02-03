import pickle
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from loguru import logger
from pydantic import model_validator

from src.data_science.ds_core.definitions.storage.base import BaseStorage


class LocalStorage(BaseStorage):
    engine: Literal["local"]
    folder: str

    @model_validator(mode="before")
    @classmethod
    def init_path(cls, data: Any) -> Any:
        # if folder is not absolute, make it absolute
        if not Path(data.get("folder")).is_absolute():
            data["path"] = Path(data.get("folder")).absolute()
        else:
            data["path"] = Path(data.get("folder"))
        return data

    def save_dataset(self, dataset: pd.DataFrame, table_name: str) -> None:
        """
        - save dataset to parquet
        """
        dataset.to_parquet(f"{self.path}/{table_name}.parquet", index=False)
        logger.info(f"Dataset {table_name} saved to {self.path}")

    def load_dataset(self, table_name: str) -> pd.DataFrame:
        """
        - load dataset from parquet
        """
        logger.info(f"Loading dataset from {self.path}/{table_name}.parquet")
        return pd.read_parquet(f"{self.path}/{table_name}.parquet")

    def save_artifact(self, artifact: Any, artifact_name: str) -> None:
        """
        - save artifact to pickle
        """
        Path(f"{self.path}/{artifact_name}.pkl").open("wb").write(pickle.dumps(artifact))
        logger.info(f"Artifact {artifact_name} saved to {self.path}")

    def load_artifact(self, artifact_name: str) -> Any:
        """
        - load artifact from pickle
        """
        artifact = pickle.load(open(f"{self.path}/{artifact_name}.pkl", "rb"))
        logger.info(f"Artifact {artifact_name} loaded from {self.path}")
        return artifact

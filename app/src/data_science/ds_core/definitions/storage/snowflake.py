import pickle
import shutil
import uuid
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from dotenv import dotenv_values
from loguru import logger
from pydantic import model_validator

from src.data_science.ds_core.definitions.storage.base import BaseStorage, DataFrame
from src.data_science.snowflake_optional import Session, get_active_session, require_snowflake


class SnowflakeStorage(BaseStorage):
    engine: Literal["snowflake"] = "snowflake"
    account: str
    user: str
    role: str
    warehouse: str
    database: str
    schema_name: str
    stage: str | None = None

    @classmethod
    def from_dotenv(cls, env_file: str = ".env") -> "SnowflakeStorage":
        config = dotenv_values(env_file)
        return cls(
            account=config.get("SNOWFLAKE_ACCOUNT"),
            user=config.get("SNOWFLAKE_USER"),
            role=config.get("SNOWFLAKE_ROLE"),
            warehouse=config.get("SNOWFLAKE_WAREHOUSE"),
            database=config.get("SNOWFLAKE_DATABASE"),
            schema_name=config.get("SNOWFLAKE_SCHEMA_NAME"),
            stage=config.get("SNOWFLAKE_STAGE"),
        )

    @model_validator(mode="before")
    @classmethod
    def init_path(cls, data: Any) -> Any:
        data["path"] = f"{data.get('database')}.{data.get('schema_name')}"
        return data

    @model_validator(mode="after")
    def setup(self):
        self._create_connection()
        self._create_schema()
        self._create_stage()

    def _get_connection(self) -> Session:
        require_snowflake()
        return get_active_session()

    def _create_connection(self):
        snowflake_credentials = {
            "user": self.user,
            "account": self.account,
            "warehouse": self.warehouse,
            "role": self.role,
            "database": self.database,
            "schema": self.schema_name,
            "authenticator": "externalbrowser",
        }
        # TODO: Add password management
        logger.info("Connecting to Snowflake...")
        Session.builder.configs(snowflake_credentials).create()
        logger.info("Connected to Snowflake")

    def _close_connection(self) -> None:
        connection = self._get_connection()
        connection.close()
        logger.info("Closed Snowflake connection")

    def save_dataset(self, dataset: DataFrame, table_name: str) -> None:
        if isinstance(dataset, pd.DataFrame):
            snowpark_df = self._create_connection().create_dataframe(dataset)
        else:
            snowpark_df = dataset
        snowpark_df.write.mode("overwrite").save_as_table(f"{self.path}.{table_name}")

    def load_dataset(self, table_name: str) -> DataFrame:
        return self._get_connection().table(f"{self.path}.{table_name}")

    def save_artifact(self, artifact: Any, artifact_name: str) -> None:
        """
        - create local tmp dir
        - save artifact to tmp dir in pkl
        - put artifact to stage
        - remove tmp dir
        """
        if self.stage is None:
            raise ValueError("Stage is not set, cannot save artifact")
        tmp_dir = self._create_local_tmp_dir()

        Path(f"{tmp_dir}/{artifact_name}.pkl").open("wb").write(pickle.dumps(artifact))
        self._get_connection().file.put(
            local_file_name=f"{tmp_dir}/{artifact_name}.pkl",
            stage_location=f"{self.path}.{self.stage}",
            overwrite=True,
            auto_compress=False,
        )
        self._remove_local_tmp_dir(tmp_dir)
        logger.info(f"Artifact {artifact_name} saved to stage {self.stage}")

    def load_artifact(self, artifact_name: str) -> Any:
        if self.stage is None:
            raise ValueError("Stage is not set, cannot load artifact")

        tmp_dir = self._create_local_tmp_dir()
        self._get_connection().file.get(
            target_directory=str(tmp_dir / f"{artifact_name}.pkl"),
            stage_location=f"{self.path}.{self.stage}.{artifact_name}",
        )
        artifact = pickle.load(open(str(tmp_dir / f"{artifact_name}.pkl"), "rb"))
        self._remove_local_tmp_dir(tmp_dir)
        logger.info(f"Artifact {artifact_name} loaded from stage {self.stage}")
        return artifact

    def _create_stage(self):
        if self.stage:
            logger.info(f"Creating stage {self.stage}")
            self._get_connection().sql(f"CREATE STAGE IF NOT EXISTS {self.stage}").collect()
            logger.info(f"Stage {self.stage} created")

    def _create_schema(self):
        if self.schema_name:
            logger.info(f"Creating schema {self.schema_name}")
            self._get_connection().sql(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}").collect()
            logger.info(f"Schema {self.schema_name} created")

    def _create_local_tmp_dir(self) -> Path:
        tmp_dir = Path(f"tmp/{uuid.uuid4()}")
        tmp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created local tmp dir {tmp_dir}")
        return tmp_dir

    def _remove_local_tmp_dir(self, tmp_dir: Path) -> None:
        shutil.rmtree(tmp_dir)
        logger.info(f"Removed local tmp dir {tmp_dir}")

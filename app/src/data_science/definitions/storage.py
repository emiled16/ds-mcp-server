from typing import Annotated, Literal

from pydantic import BaseModel, Field

from src.data_science.definitions.table import LocalTable, SnowflakeTable, Table


class SnowflakeStorageConfig(BaseModel):
    storage: Literal["snowflake"] = "snowflake"
    database_name: str
    schema_name: str
    table_name: str

    def to_table(self) -> Table:
        return SnowflakeTable(
            database_name=self.database_name,
            schema_name=self.schema_name,
            table_name=self.table_name,
        )


class LocalStorageConfig(BaseModel):
    storage: Literal["local"] = "local"
    directory: str
    file_name: str

    def to_table(self) -> Table:
        return LocalTable(directory=self.directory, file_name=self.file_name)


StorageConfig = Annotated[SnowflakeStorageConfig | LocalStorageConfig, Field(discriminator="storage")]

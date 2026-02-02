from typing import Annotated, Union

from pydantic import Field

from src.data_science.ds_core.definitions.storage.base import BaseStorage
from src.data_science.ds_core.definitions.storage.local import LocalStorage
from src.data_science.ds_core.definitions.storage.snowflake import SnowflakeStorage

__all__ = ["BaseStorage", "LocalStorage", "SnowflakeStorage"]

Storage = Annotated[Union[LocalStorage, SnowflakeStorage], Field(discriminator="engine")]

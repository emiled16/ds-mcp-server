import os
from typing import Optional

import pandas as pd
from snowflake.snowpark.context import get_active_session

from src.data_science.ds_core.definitions.storage.snowflake import SnowflakeStorage
from src.data_science.ds_core.snowflake import snowflake_session


def load_data_from_snowflake(query: str) -> pd.DataFrame:
    # Create connection and get session
    session = snowflake_session()
    result = session.sql(query).to_pandas()

    return result


def load_data_from_csv(file: str) -> pd.DataFrame:
    return pd.read_csv(file)

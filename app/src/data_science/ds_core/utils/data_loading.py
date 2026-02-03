import pandas as pd

from src.data_science.ds_core.snowflake import snowflake_session
from src.data_science.snowflake_optional import require_snowflake


def load_data_from_snowflake(query: str) -> pd.DataFrame:
    require_snowflake()
    # Create connection and get session
    session = snowflake_session()
    result = session.sql(query).to_pandas()

    return result


def load_data_from_csv(file: str) -> pd.DataFrame:
    return pd.read_csv(file)

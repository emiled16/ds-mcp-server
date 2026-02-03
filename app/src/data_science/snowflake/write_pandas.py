import logging
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from pandas.core.dtypes.common import is_datetime64_any_dtype
from src.data_science.snowflake.data_types import VARIANT_TYPES
from src.data_science.snowflake.identifiers import TablePath, identifier_parts
from src.data_science.snowflake_optional import Session, require_snowflake

logger = logging.getLogger(__name__)


def write_pandas(session: Session, table_path: TablePath, df: pd.DataFrame) -> None:
    require_snowflake()
    """Insert rows in the given data frame to the given table.

    This is a re-implementation of the `write_pandas` function that supports variants, dates and binaries.
    Basically this:
    - Saves the data frame to a Parquet file.
    - Uses `PUT` to upload the file to the table stage.
    - Uses `COPY INTO <table>` to copy the data from the parquet file into the table.

    See:
    - https://docs.snowflake.com/en/user-guide/script-data-load-transform-parquet.html#sql-script-1-load-parquet-data
    - https://docs.snowflake.com/en/user-guide/python-connector-api.html#write_pandas
    """
    if df.empty:
        return

    logger.debug(f"Inserting {len(df)} rows to the {table_path.upper()} table...")

    table_cols = session.sql(f"DESCRIBE TABLE {table_path}").collect()
    column_types = {str(col["name"]).lower(): str(col["type"]) for col in table_cols}

    database, schema, table = identifier_parts(session, table_path)
    table_stage = f"@{database}.{schema}.%{table}"

    # Store the dataframe as a temporary Parquet file and send it to snowflake
    with TemporaryDirectory() as tmp_folder:
        file_path = Path(tmp_folder) / "file.parquet"
        df.to_parquet(file_path)
        session.file.put(str(file_path), table_stage, overwrite=True)
        file_path.unlink()  # Remove file

    fields = ", ".join(_parse_field(col, df.dtypes[col], column_types[col]) for col in df.columns)

    # See: https://docs.snowflake.com/en/sql-reference/sql/copy-into-table.html
    session.sql(
        f"""
        COPY INTO {table_path} ({", ".join(df.columns)})
        FROM (SELECT {fields} FROM {table_stage})
        FILE_FORMAT = (TYPE = PARQUET)
        PURGE = TRUE
        ON_ERROR = ABORT_STATEMENT
        """,
    ).collect()


def _parse_field(column: str, dtype: str, snowflake_type: str) -> str:
    """Return the Snowflake expression to select the given column from a staged Parquet document.

    Examples results:
    - "$1:column_a"
    - "PARSE_JSON($1:column_b)"
    - "$1:column_c::BINARY(16)"
    - "TO_TIMESTAMP($1:column_d::INTEGER, 9)"

    See: https://docs.snowflake.com/en/user-guide/script-data-load-transform-parquet.html#sql-script-1-load-parquet-data
    """
    field = f"$1:{column}"  # $1 is the Parquet document, from which we get the given column

    if snowflake_type in VARIANT_TYPES:
        return f"PARSE_JSON({field})"

    if snowflake_type.startswith("BINARY"):
        return f"{field}::{snowflake_type}"  # Binary must be casted

    if is_datetime64_any_dtype(dtype):
        return f"TO_TIMESTAMP({field}::INTEGER, 9)"  # Parquet stores datetime64 as a nanosecond timestamp

    return field

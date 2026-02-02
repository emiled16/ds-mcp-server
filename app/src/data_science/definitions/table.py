import re
from pathlib import Path
from typing import Annotated, Any, Union

import pandas as pd
from pydantic import AfterValidator, BaseModel
from snowflake.snowpark import DataFrame, Session


def quote_db_identifier(name: str) -> str:
    """Return an identifier to reference the given object name in a SQL query (table, schema, database).
    It double quotes the name when it is non standard (not SCREAM_CASE).
    """
    if name.startswith('"') and name.endswith('"'):
        return name

    return name if re.match(r"^[A-Z_][A-Z0-9_]*$", name) else f'"{name}"'


DbIdentifier = Annotated[str, AfterValidator(quote_db_identifier)]


def unquote_db_identifier(name: DbIdentifier) -> str:
    return name[1:-1] if name.startswith('"') and name.endswith('"') else name


class SnowflakeTable(BaseModel):
    """
    A table that is specified by a database name, schema name, and table name. (snowflake)
    """

    database_name: DbIdentifier
    schema_name: DbIdentifier
    table_name: DbIdentifier

    def path(self) -> str:
        return f"{self.database_name}.{self.schema_name}.{self.table_name}"

    def materialize(self, session: Session) -> DataFrame:
        return session.table(self.path())

    def to_pandas(self, session: Session) -> pd.DataFrame:
        rows = self.materialize(session=session).collect()
        return pd.DataFrame([o.as_dict() for o in rows])


class LocalTable(BaseModel):
    """
    A table that is specified by a directory and file name. (local)
    """

    directory: str
    file_name: str

    def path(self) -> str:
        # return Path.cwd() / self.directory / self.file_name
        return str(Path(r"C:\Users\h228rvh\dev\maxa-poc\data-science") / self.directory / self.file_name)

    def to_materialize(self) -> None:
        pass

    def to_pandas(self, **kwargs: Any) -> pd.DataFrame:
        return pd.read_csv(self.path(), **kwargs)


Table = Union[SnowflakeTable, LocalTable]

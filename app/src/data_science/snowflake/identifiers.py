import re
from typing import Optional, Tuple

from pydantic import AfterValidator
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark.session import Session
from typing_extensions import Annotated

IDENTIFIER_REGEX = r"[A-Z_][A-Z0-9_]*"
QUOTED_IDENTIFIER_REGEX = r'"[^"]+"'  # Anything within double quotes


def db_identifier(name: str) -> "DbIdentifier":
    """Return an identifier to reference the given object name in a SQL query (table, schema, database).

    It double quotes the name when it is non standard (not SCREAM_CASE).
    """
    if re.match(rf'^"{IDENTIFIER_REGEX}"$', name):  # Quoted good identifier
        return unquote_db_identifier(name)

    if name.startswith('"') and name.endswith('"'):  # Quoted identifier
        return name

    return name if re.match(rf"^{IDENTIFIER_REGEX}$", name) else f'"{name}"'


DbIdentifier = Annotated[str, AfterValidator(db_identifier)]


def is_table_path(table_path: str) -> "TablePath":
    """Validate that the given path can be fully qualified."""
    any_identifier_regex = rf"(?:{IDENTIFIER_REGEX}|{QUOTED_IDENTIFIER_REGEX})"
    table_path_regex = rf"^{any_identifier_regex}(\.{any_identifier_regex})?(\.{any_identifier_regex})?$"

    if not re.match(table_path_regex, table_path):
        raise ValueError(f"Invalid table path: {table_path} (must be uppercase)")

    return table_path


def full_table_path(session: Session, table_path: str) -> "FullTablePath":
    """Return an full path "{database}.{schema}.{table}" from the given partial path."""
    table_path = is_table_path(table_path)
    database, schema, table = identifier_parts(session, table_path)
    if database is None or schema is None:
        raise ValueError(f"Database or schema not in session context: {database=}, {schema=}")

    return f"{db_identifier(database)}.{db_identifier(schema)}.{db_identifier(table)}"


TablePath = Annotated[str, AfterValidator(is_table_path)]
FullTablePath = Annotated[str, AfterValidator(lambda value: full_table_path(get_active_session(), value))]


def unquote_db_identifier(name: DbIdentifier) -> str:
    return name[1:-1] if name.startswith('"') and name.endswith('"') else name


def current_database(session: Session) -> Optional[DbIdentifier]:
    if database := session.get_current_database():
        return db_identifier(database)
    return None


def current_schema(session: Session) -> Optional[DbIdentifier]:
    if schema := session.get_current_schema():
        return db_identifier(schema)
    return None


def identifier_parts(session: Session, table_path: TablePath) -> Tuple[Optional[str], Optional[str], str]:
    """Return the triple (database, schema, table) from the given path."""
    # TODO: python 3.10 - rewrite using `match` statement
    # => https://github.com/maxa-ai/maxa-console-streamlit-client_apps/blob/6701434cda6c479cb3d5a9089812ea95dc490f53/libs/maxa/snowflake/maxa/snowflake/identifiers.py#L45-L55
    parts = table_path.split(".")

    if len(parts) == 3:
        database, schema, table = parts
        return database, schema, table

    if len(parts) == 2:
        schema, table = parts
        return current_database(session), schema, table

    if len(parts) == 1:
        table = parts[0]
        return current_database(session), current_schema(session), table

    raise ValueError(f"Invalid table path: {table_path}")

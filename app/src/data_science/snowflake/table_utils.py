from snowflake.snowpark.session import Session

from src.data_science.snowflake.identifiers import db_identifier, identifier_parts, unquote_db_identifier


def table_exists(session: Session, table_path: str) -> bool:
    """Return true if the given table exists."""
    database, schema, table = identifier_parts(session, table_path)

    if not database or not schema:
        raise ValueError(f"No database nor schema in path {table_path} or in current session.")

    result = session.sql(
        f"""
        select count(*) as nb_tables
        from {db_identifier(database)}.information_schema.tables
        where table_schema = ? and table_name = ?
        """,
        params=[unquote_db_identifier(schema), unquote_db_identifier(table)],
    ).collect()

    return len(result) == 1 and result[0]["NB_TABLES"] == 1

from snowflake.snowpark import Session
from sqlalchemy import Engine, create_engine, text


def get_engine_from_session(session: Session) -> Engine:
    # Your existing Snowflake connection (replace with your actual connection)
    existing_snowflake_connection = session._conn._conn  # noqa: SLF001
    existing_snowflake_connection._interpolate_empty_sequences = False
    # sql alchemy needs pyformat binding
    existing_snowflake_connection._paramstyle = "pyformat"  # noqa: SLF001
    opts = ""
    if session.get_current_warehouse() is not None:
        opts += f"&warehouse={session.get_current_warehouse()}"
    if session.get_current_role() is not None:
        opts += f"&role={session.get_current_role()}"
    conn_url = (
        f"snowflake://{session.get_current_user() or ''}@{session.get_current_account()}/"
        f"{session.get_current_database() or ''}/{session.get_current_schema() or ''}?{opts}"
    )
    # Create an engine and bind it to the existing Snowflake connection
    engine = create_engine(
        url=conn_url,
        creator=lambda: existing_snowflake_connection,
    )

    with engine.connect() as conn:
        conn.execute(text("ALTER SESSION SET AUTOCOMMIT = TRUE"))
        conn.commit()

    return engine

import threading
from collections.abc import Generator
from contextlib import contextmanager

from src.data_science.snowflake_optional import Session, get_active_session, require_snowflake

_transaction_lock = threading.RLock()
_in_transaction: bool = False


@contextmanager
def snowflake_transaction() -> Generator[Session, None, None]:
    """Context wrapping the executed SQL queries in a Snowflake transaction."""
    require_snowflake()
    with _transaction_lock:  # Prevent threads to share transactions
        global _in_transaction  # noqa: PLW0603 - Shared state for nested transactions

        session = get_active_session()

        # Snowflake does not manage nested transactions
        if _in_transaction:
            yield session
            return

        session.sql("begin transaction").collect()
        _in_transaction = True
        try:
            yield session
            session.sql("commit").collect()
        except Exception:
            session.sql("rollback").collect()
            raise
        finally:
            _in_transaction = False

import threading
from contextlib import contextmanager
from typing import Generator

from snowflake.snowpark import Session
from snowflake.snowpark.context import get_active_session

_transaction_lock = threading.RLock()
_in_transaction: bool = False


@contextmanager
def snowflake_transaction() -> Generator[Session, None, None]:
    """Context wrapping the executed SQL queries in a Snowflake transaction."""
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

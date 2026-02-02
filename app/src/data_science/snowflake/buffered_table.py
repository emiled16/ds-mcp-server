import atexit
import threading
from types import TracebackType
from typing import Any, Dict, List, Optional, Type

from snowflake.snowpark import Session

from src.data_science.snowflake.constants import SNOWFLAKE_INSERT_MAX_NB_ROWS
from src.data_science.snowflake.data_types import VARIANT_TYPES, DataType, serialize_variant


class BufferedTable:
    """Snowflake table buffered to avoid multiple requests, so the buffer must be flushed."""

    def __init__(
        self,
        session: Session,
        table_path: str,
        columns: Dict[str, DataType],
        capacity: int = SNOWFLAKE_INSERT_MAX_NB_ROWS,
    ) -> None:
        self._session = session
        self._table_path = table_path
        self._columns = columns

        self._capacity = capacity
        self._buffer: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

        atexit.register(self.flush)  # automatically flush when stopping the app

    def add(self, row: Dict[str, Any]) -> "BufferedTable":
        # Inspired by logging.BufferingHandler
        # => https://github.com/python/cpython/blob/3.12/Lib/logging/handlers.py#L1307-L1325
        with self._lock:
            self._buffer.append(row)
            if len(self._buffer) >= self._capacity - 1:
                self.flush()

        return self

    def flush(self) -> None:
        """Flush all rows in the buffer to the Snowflake table."""
        with self._lock:
            if len(self._buffer) == 0:
                return

            try:
                # Generate a query looking like this:
                # ```
                # insert into my_table (col1, col2, col3, col4)
                # select $1, $2, parse_json($3), $4
                # from values
                #     (?, ?, ?, ?),
                #     (?, ?, ?, ?),
                #     (?, ?, ?, ?);
                # ```
                # With the VARIANT columns using `parse_json` and values parametrized.

                cols = ", ".join(self._columns)
                selects = ", ".join(
                    f"parse_json(${index + 1})" if dtype in VARIANT_TYPES else f"${index + 1}"
                    for index, dtype in enumerate(self._columns.values())
                )
                cols_placeholders = "(" + ", ".join("?" * len(self._columns)) + ")"

                parametrized_values = tuple(
                    serialize_variant(row.get(col)) if dtype in VARIANT_TYPES else row.get(col)
                    for row in self._buffer
                    for col, dtype in self._columns.items()
                )

                self._session.sql(
                    f"""
                    insert into {self._table_path} ({cols})
                    select {selects}
                    from values {", ".join(cols_placeholders for _ in self._buffer)}
                    """,
                    params=parametrized_values,
                ).collect()

                self._buffer.clear()

            except Exception as error:
                # TODO: log about failure to write in the table
                nb_rows = len(self._buffer)
                raise RuntimeError(f"Failed to insert {nb_rows} rows into {self._table_path}: {error}") from error

    def __enter__(self) -> "BufferedTable":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]] = None,
        exc_val: Optional[BaseException] = None,
        exc_tb: Optional[TracebackType] = None,
    ) -> None:
        self.flush()

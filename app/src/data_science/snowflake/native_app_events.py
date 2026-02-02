from datetime import datetime, timezone
from textwrap import dedent
from types import TracebackType
from typing import Any, Dict, List, Optional, Type
from uuid import uuid4

import pandas as pd
import snowflake.snowpark.functions as sf
from snowflake.snowpark import Session

from src.data_science.snowflake.buffered_table import BufferedTable

# TODO(MAX-497): move OPERATIONS to CORE
EVENT_TABLE_PATH = "OPERATIONS.MAXA_EVENTS"


class NativeAppEvents:
    """Manage events from the different components of the application."""

    @staticmethod
    def definition(table_path: str = EVENT_TABLE_PATH) -> str:
        # TODO(MAX-497): currently using the definition in ACME setup scripts here:
        #   => https://github.com/maxa-ai/maxa-client-acme-corporation/blob/4d8587a2ddc4edf099aeea526f456b5ba08d1c01/deployment/native-application/scripts/schemas_operations.sql#L31-L36
        #   Will need to be moved to a centralized place eventually.
        return dedent(
            f"""
            CREATE TABLE IF NOT EXISTS {table_path} (
                SOURCE string,
                UUID varchar(36) unique default uuid_string(),
                PAYLOAD variant,
                CREATED_AT timestamp_tz default current_timestamp()
            ) comment='Events from the different components of the application';
            """,
        )

    def __init__(self, session: Session, source: str, table_path: str = EVENT_TABLE_PATH) -> None:
        self._session = session
        self._source = source
        self._table_path = table_path
        self._buffered_table = BufferedTable(
            session=session,
            table_path=table_path,
            columns={
                "source": "TEXT",
                "uuid": "TEXT",
                "payload": "VARIANT",
                "created_at": "TIMESTAMP_NTZ",
            },
        )

    def emit(self, payload: Dict[str, Any], uuid: Optional[str] = None) -> "NativeAppEvents":
        """Prepare an event to be sent."""
        self._buffered_table.add(
            {
                "source": self._source,
                "uuid": uuid or str(uuid4()),
                "payload": payload,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return self

    def publish(self) -> None:
        """Effectively send the events."""
        self._buffered_table.flush()

    def fetch_events(
        self,
        source: Optional[str] = None,
        delta_hours: Optional[int] = None,
        columns: Optional[List[str]] = None,
        with_payload: Optional[Dict[str, str]] = None,
    ) -> pd.DataFrame:
        query = self._session.table(self._table_path).filter(
            sf.col("source") == (source if source else self._source),
        )

        if delta_hours:
            threshold = datetime.now(timezone.utc) - pd.Timedelta(hours=delta_hours)
            query = query.filter(sf.col("created_at") >= threshold).sort(sf.col("created_at").desc())
        if with_payload:
            for key, value in with_payload.items():
                query = query.filter(sf.get_path(sf.col("payload"), sf.lit(key)) == value)
        return query.select(columns or "*").to_pandas()

    def __enter__(self) -> "NativeAppEvents":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]] = None,
        exc_val: Optional[BaseException] = None,
        exc_tb: Optional[TracebackType] = None,
    ) -> None:
        self.publish()


# Global instance to keep a single buffer of events
__native_app_events: Optional[NativeAppEvents] = None


def setup_native_app_events(
    session: Session,
    source: str,
    table_path: str = EVENT_TABLE_PATH,
) -> NativeAppEvents:
    global __native_app_events
    if __native_app_events is not None:
        return __native_app_events

    __native_app_events = NativeAppEvents(session, source, table_path)
    return __native_app_events


def native_app_events() -> NativeAppEvents:
    global __native_app_events
    if not __native_app_events:
        raise ValueError("Call setup_native_app_events prior to this call.")

    return __native_app_events

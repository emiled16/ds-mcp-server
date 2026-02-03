import json
import logging
import logging.handlers
import os
from datetime import datetime, timezone
from enum import Enum
from textwrap import dedent
from types import TracebackType
from typing import Any

from src.data_science.snowflake.buffered_table import BufferedTable
from src.data_science.snowflake.session import create_snowpark_session
from src.data_science.snowflake_optional import Session, col, count, lit, lower, require_snowflake

SNOWFLAKE_LOGS_TABLE_NAME = "OPERATIONS.MAXA_LOGS"


class LogAudiences(Enum):
    INTERNAL = "internal"
    CUSTOMER = "customer"


class NativeAppLogger:
    """Logger that can be used from any Python app within a Native App.

    A Native App can contain multiple components (like containers or streamlit applications),
    the purpose of this library is to be used within all of the different components (admin-app,
    translate runner, etc.).

    The idea is fairly simple: avoid writing to stdout and stderr as everything ends up in the event log.
    Instead, the MaxaLogger writes to a Snowflake table all of the log messages above a specified log level.
    Furthermore, a second logger will print to stdout/stderr if the message is above ERROR or if it's marked
    with a LogAudiences.CUSTOMER.
    """

    def __init__(
        self,
        app_name: str,
        logger_name: str,
        session: Session,
        table_path: str,
        extra_fields: dict[str, Any],
    ):
        require_snowflake()
        self._table_path = table_path
        self._app_name = app_name
        self._internal_logger = logging.getLogger(logger_name)
        self._internal_logger.setLevel(logging.ERROR)

        self._env = os.getenv("APP_DEPLOYMENT_STAGE", "local")
        self._version = os.getenv("APP_VERSION", "0.0.0")
        self._extra_fields = {"env": self._env, "version": self._version, **extra_fields}
        self._maxa_logger = None
        if _log_table_exists(session, table_path):
            level = logging.DEBUG if self._env == "local" else logging.WARNING
            if env_log_level := os.getenv("APP_LOG_LEVEL"):
                level = _validate_log_level(env_log_level)
            self._maxa_logger = SnowflakeTableLogger(session, table_path, logger_name, level)
        else:
            self._internal_logger.error(f"Table `{table_path}` does not exist. SnowflakeLogger is disabled.")

    def _log(
        self,
        message: str,
        audience: LogAudiences,
        level: int = logging.NOTSET,
        is_exception: bool = False,
        **extra,
    ) -> None:
        msg = {
            "message": message,
            **self._extra_fields,
            **extra,
        }
        json_msg = json.dumps(obj=msg, separators=(",", ":"), default=str)

        if audience == LogAudiences.CUSTOMER and is_exception:
            self._internal_logger.exception(msg=json_msg)
        elif audience == LogAudiences.CUSTOMER:
            self._internal_logger.log(level=level, msg=json_msg)

        if self._maxa_logger:
            self._maxa_logger.log(level=level, msg=json_msg, source=self._app_name, audience=audience)

    def debug(self, message: str, audience: LogAudiences = LogAudiences.INTERNAL, **extra) -> None:
        self._log(message=message, audience=audience, level=logging.DEBUG, **extra)

    def info(self, message: str, audience: LogAudiences = LogAudiences.INTERNAL, **extra) -> None:
        self._log(message=message, audience=audience, level=logging.INFO, **extra)

    def warning(self, message: str, audience: LogAudiences = LogAudiences.INTERNAL, **extra) -> None:
        self._log(message=message, audience=audience, level=logging.WARNING, **extra)

    def error(self, message: str, audience: LogAudiences = LogAudiences.INTERNAL, **extra) -> None:
        self._log(message=message, audience=audience, level=logging.ERROR, **extra)

    def critical(self, message: str, audience: LogAudiences = LogAudiences.INTERNAL, **extra) -> None:
        self._log(message=message, audience=audience, level=logging.CRITICAL, **extra)

    def exception(self, message: str, audience: LogAudiences = LogAudiences.INTERNAL, **extra) -> None:
        self._log(message=message, audience=audience, level=logging.ERROR, is_exception=True, **extra)

    def log_table(self) -> str:
        return self._table_path

    def __enter__(self) -> "NativeAppLogger":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: TracebackType | None = None,
    ) -> None:
        if self._maxa_logger:
            self._maxa_logger.flush()

    @staticmethod
    def definition(table_path: str) -> str:
        # TODO(MAX-497): currently using the definition in ACME setup scripts here:
        #   => https://github.com/maxa-ai/maxa-client-acme-corporation/blob/290c8c246efac531afc3e4cead95fee48eb70929/deployment/native-application/scripts/schemas_operations.sql#L15-L22
        #   Will need to be moved to a centralized place eventually.
        return dedent(
            f"""
            CREATE TABLE IF NOT EXISTS {table_path} (
                LEVEL string default '',
                RUN_ID string default '',
                AUDIENCE string default 'internal',
                SOURCE string default '',
                MSG string,
                CREATED_AT timestamp_tz default current_timestamp()
            ) comment='Internal log table';
            """,
        )


def _validate_log_level(value: str) -> int:
    value = logging.getLevelName(value)
    if isinstance(value, int):
        return value
    raise ValueError(f"The log level '{value}' is invalid")


def _log_table_exists(session: Session, table_name: str) -> bool:
    split = table_name.split(".")
    if len(split) != 2:
        raise ValueError(f"table_name should be in the format `schema.table_name`, but got {table_name}.")
    schema, table = split
    result = (
        session.table("information_schema.tables")
        .filter((lower(col("table_schema")) == lower(lit(schema))) & (lower(col("table_name")) == lower(lit(table))))
        .select(count("*").alias("count"))
        .collect()
    )
    return len(result) == 1 and result[0]["COUNT"] == 1


class SnowflakeTableLogger:
    # https://docs.python.org/3/howto/logging-cookbook.html#buffering-logging-messages-and-outputting-them-conditionally
    def __init__(self, session: Session, table_path: str, logger_name: str, level: int, capacity: int = 50):
        self._session = session
        self._table_path = table_path
        self._logger_name = logger_name
        self._level = level

        self._buffered_table = BufferedTable(
            session=session,
            table_path=table_path,
            columns={
                "level": "TEXT",
                "audience": "TEXT",
                "source": "TEXT",
                "msg": "TEXT",
                "created_at": "TIMESTAMP_NTZ",
            },
        )

    def log(self, level: int, msg: str, source: str, audience: LogAudiences) -> None:
        if level >= self._level:
            sql_message = msg[0:16000000] if len(msg) > 16000000 else msg
            self._buffered_table.add(
                {
                    "level": logging.getLevelName(level),
                    "audience": audience.value,
                    "source": source,
                    "msg": sql_message,
                    "created_at": datetime.now(timezone.utc),
                },
            )

    def flush(self) -> None:
        self._buffered_table.flush()


__native_app_logger: NativeAppLogger | None = None


def init_native_app_logger(
    app_name: str,
    logger_name: str | None = None,
    session: Session | None = None,
    table_name: str = SNOWFLAKE_LOGS_TABLE_NAME,
    extra_fields: dict[str, Any] = {},
) -> None:
    global __native_app_logger
    if __native_app_logger is None:
        __native_app_logger = NativeAppLogger(
            app_name,
            logger_name or "maxa_native_app_logger",
            session or create_snowpark_session(),
            table_name,
            extra_fields,
        )


def native_app_logger() -> NativeAppLogger:
    if not __native_app_logger:
        raise ValueError("Call NativeAppLogger.init prior to this call.")
    return __native_app_logger

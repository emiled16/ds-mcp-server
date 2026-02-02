"""Structured logging configuration.

Provides structured logging with correlation IDs for tracing tool calls
across the system.
"""

import contextvars
import sys
import uuid
from typing import Any

import structlog
from loguru import logger

# Context variable for request/correlation ID
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id",
    default="",
)


def get_correlation_id() -> str:
    """Get current correlation ID or generate a new one."""
    cid = correlation_id_var.get()
    if not cid:
        cid = str(uuid.uuid4())[:8]
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_var.set(cid)


def add_correlation_id(
    logger: structlog.BoundLogger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add correlation ID to log event."""
    event_dict["correlation_id"] = get_correlation_id()
    return event_dict


def configure_structlog() -> None:
    """Configure structlog for structured JSON logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            add_correlation_id,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def configure_loguru(json_format: bool = False) -> None:
    """Configure loguru for application logging.

    Args:
        json_format: If True, output JSON logs; otherwise pretty-print
    """
    # Remove default handler
    logger.remove()

    # Add custom handler with correlation ID
    if json_format:
        log_format = (
            '{{"timestamp": "{time:YYYY-MM-DDTHH:mm:ss.SSS}", '
            '"level": "{level.name}", '
            '"correlation_id": "{extra[correlation_id]}", '
            '"module": "{module}", '
            '"function": "{function}", '
            '"line": {line}, '
            '"message": "{message}"}}'
        )
    else:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>[{extra[correlation_id]}]</cyan> | "
            "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    logger.add(
        sys.stdout,
        format=log_format,
        level="INFO",
        colorize=not json_format,
        backtrace=True,
        diagnose=True,
    )

    # Bind correlation ID to logger
    logger.configure(
        extra={"correlation_id": lambda: get_correlation_id()},
    )


def get_logger(name: str | None = None) -> Any:
    """Get a logger instance with correlation ID support.

    Args:
        name: Optional logger name (module name)

    Returns:
        Logger instance
    """
    return logger.bind(correlation_id=get_correlation_id())


class LoggingMiddleware:
    """Middleware to add correlation ID and logging to tool calls."""

    @staticmethod
    def before_tool(tool_name: str, args: tuple, kwargs: dict) -> str:
        """Called before tool execution.

        Returns:
            Correlation ID for this call
        """
        cid = str(uuid.uuid4())[:8]
        set_correlation_id(cid)

        log = get_logger()
        log.info(
            f"Tool call started: {tool_name}",
            tool=tool_name,
            args=str(args)[:100],
            kwargs_keys=list(kwargs.keys()),
        )

        return cid

    @staticmethod
    def after_tool(
        tool_name: str,
        cid: str,
        success: bool,
        duration_ms: float,
        error: str | None = None,
    ) -> None:
        """Called after tool execution."""
        log = get_logger()

        if success:
            log.info(
                f"Tool call completed: {tool_name}",
                tool=tool_name,
                duration_ms=round(duration_ms, 2),
                success=True,
            )
        else:
            log.error(
                f"Tool call failed: {tool_name}",
                tool=tool_name,
                duration_ms=round(duration_ms, 2),
                success=False,
                error=error,
            )

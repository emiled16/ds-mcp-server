"""PostgreSQL engine from DATABASE_URL."""

import os

from sqlalchemy import Engine, create_engine

# Default for local dev if DATABASE_URL not set (override in .env)
_DEFAULT_URL = "postgresql+psycopg2://localhost:5432/maxa_ds"


def get_engine(url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine for PostgreSQL.

    Uses DATABASE_URL from environment if url is not provided.
    Format: postgresql+psycopg2://user:password@host:port/dbname
    """
    connection_url = url or os.getenv("DATABASE_URL", _DEFAULT_URL)
    # Allow postgres:// (Heroku-style) to work with psycopg2
    if connection_url.startswith("postgres://"):
        connection_url = connection_url.replace("postgres://", "postgresql+psycopg2://", 1)
    return create_engine(
        connection_url,
        pool_pre_ping=True,
        echo=os.getenv("SQL_ECHO", "").lower() in ("1", "true", "yes"),
    )

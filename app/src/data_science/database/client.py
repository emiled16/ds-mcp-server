"""PostgreSQL database client using SQLAlchemy and pandas."""

import datetime
import shutil
from collections.abc import Hashable
from pathlib import Path
from typing import Any, Dict, List, Literal, Type, TypeVar

import pandas as pd
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import Engine, insert, text

from src.data_science.database.base import Base

T = TypeVar("T", bound=Base)


def table_path_from_orm(table_orm: Type[T]) -> str:
    """Return schema-qualified table name for the ORM class."""
    t = table_orm.__table__
    return f'"{t.schema}"."{t.name}"' if t.schema else f'"{t.name}"'


class Qualify(BaseModel):
    """Row selection by window function (e.g. latest per partition)."""

    fn: Literal["row_number"] = "row_number"
    partition_by: list[str] | None = None
    order_by: list[str] | None = None
    asc: bool = True
    target: int | None = None

    def to_sql_subquery(self, table_path: str, where_clause: str = "") -> str:
        """Return SQL for selecting rows with ROW_NUMBER() applied."""
        order_cols = self.order_by or ["1"]
        order_dir = "ASC" if self.asc else "DESC"
        order_expr = ", ".join(f'"{c}" {order_dir}' for c in order_cols)
        partition = f"PARTITION BY {', '.join(f'\"{c}\"' for c in self.partition_by)}" if self.partition_by else ""
        over = f"OVER ({partition} ORDER BY {order_expr})"
        where = f" WHERE {where_clause}" if where_clause else ""
        return f"""
            SELECT * FROM (
                SELECT *, ROW_NUMBER() {over} AS rn
                FROM {table_path}{where}
            ) sub
            WHERE rn = {self.target or 1}
        """


class DBClient:
    """PostgreSQL client for experiment/run/feature-store tables and file storage."""

    def __init__(
        self,
        engine: Engine,
        file_storage_path: Path | str | None = None,
    ) -> None:
        self._engine = engine
        self._file_storage_path = Path(file_storage_path) if file_storage_path else None

    def insert_records(self, table_orm: Type[T], records: List[Dict[str, Any]]) -> None:
        if not records:
            return
        table = table_orm.__table__
        with self._engine.begin() as conn:
            conn.execute(insert(table), records)

    def fetch_records(
        self,
        table_orm: Type[T],
        filters: dict[str, Any],
        qualify: Qualify | None = None,
    ) -> list[dict[Hashable, Any]]:
        table_path = table_path_from_orm(table_orm)
        where_parts = [f'"{k}" = :{k}' for k in filters.keys()]
        where_clause = " AND ".join(where_parts) if where_parts else ""

        if qualify is not None:
            sql = qualify.to_sql_subquery(table_path, where_clause)
            df = pd.read_sql(text(sql), self._engine, params=filters)
        else:
            base_sql = f'SELECT * FROM {table_path}'
            if where_clause:
                base_sql += f" WHERE {where_clause}"
            df = pd.read_sql(text(base_sql), self._engine, params=filters)

        return df.rename(columns=str.lower).to_dict(orient="records")

    def append_table(self, table_orm: Type[T], df: pd.DataFrame) -> None:
        if len(df) == 0:
            return
        table = table_orm.__table__
        schema = table.schema or "public"
        name = table.name
        df = df.rename(columns=str.lower)
        with self._engine.begin() as conn:
            df.to_sql(name, conn, schema=schema, if_exists="append", index=False, method="multi")

    def fetch_table(self, table_path: str, filters: dict[str, Any] | None = None) -> pd.DataFrame:
        """Fetch a table as a DataFrame, optionally filtered.

        table_path: schema-qualified name, e.g. forecasting_experiment_data.dim_runs
                   or quoted "schema"."name" from table_path_from_orm()
        """
        if table_path.startswith('"'):
            full_name = table_path
        elif "." in table_path:
            schema, name = table_path.split(".", 1)
            full_name = f'"{schema}"."{name}"'
        else:
            full_name = f'"{table_path}"'
        sql = f"SELECT * FROM {full_name}"
        params = {}
        if filters:
            where_parts = [f'"{k}" = :{k}' for k in filters]
            sql += " WHERE " + " AND ".join(where_parts)
            params = filters
        return pd.read_sql(text(sql), self._engine, params=params).rename(columns=str.lower)

    def upload_files(self, path: Path, identifier: str, stage: str | None = None) -> str | None:
        """Copy local files to storage under identifier. Returns storage path or None."""
        if self._file_storage_path is None:
            logger.warning("FILE_STORAGE_PATH not set; upload_files no-op")
            return None
        dest = self._file_storage_path / identifier
        dest.mkdir(parents=True, exist_ok=True)
        for item in path.rglob("*"):
            if item.is_file():
                rel = item.relative_to(path)
                (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest / rel)
        return str(dest)

    def download_files(self, path: Path, identifier: str, stage: str | None = None) -> None:
        """Copy files from storage to local path."""
        if self._file_storage_path is None:
            raise ValueError("FILE_STORAGE_PATH not set; cannot download_files")
        src = self._file_storage_path / identifier
        if not src.exists():
            raise FileNotFoundError(f"Storage path not found: {src}")
        path.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, path, dirs_exist_ok=True)
        else:
            shutil.copy2(src, path)


def categorize_column(col: Any) -> str:
    """Map Python type to a simple category name (for compatibility)."""
    if isinstance(col, str):
        return "TEXT"
    if isinstance(col, int):
        return "NUMBER"
    if isinstance(col, float):
        return "FLOAT"
    if isinstance(col, bool):
        return "BOOLEAN"
    if isinstance(col, (datetime.datetime, pd.Timestamp)):
        return "TIMESTAMP"
    return "TEXT"

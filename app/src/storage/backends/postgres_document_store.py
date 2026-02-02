"""PostgreSQL document store implementing the DocumentStore interface.

Uses schema `app` and a single table `app.documents(collection, entity_id, data JSONB)`.
Replaces MongoDB for jobs, notes, and tool responses.
"""

import json
import os
import re
import uuid
from typing import Any

import asyncpg

from src.storage.interfaces import DocumentStore


def _build_where_and_params(query: dict, param_start: int = 1) -> tuple[str, list[Any]]:
    """Build SQL WHERE clause and params from a Mongo-style query dict.

    Supports: equality {"k": "v"}, $in {"k": {"$in": [a,b]}}, $regex {"k": {"$regex": "p", "$options": "i"}},
    $or [{"k": "v"}, ...]. param_start: first placeholder number (e.g. 2 when $1 is used for collection).
    """
    conditions: list[str] = []
    params: list[Any] = []
    param_idx = [param_start - 1]

    def next_param(val: Any) -> str:
        param_idx[0] += 1
        params.append(val)
        return f"${param_idx[0]}"

    def escape_key(k: str) -> str:
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", k):
            raise ValueError(f"Unsafe key for JSONB: {k}")
        return k

    def handle_value(key: str, val: Any) -> str:
        key = escape_key(key)
        if isinstance(val, dict):
            if "$in" in val:
                arr = val["$in"]
                p = next_param([str(x) for x in arr])
                return f"(data->>'{key}' = ANY({p}::text[]))"
            if "$regex" in val:
                pattern = val["$regex"]
                p = next_param(pattern)
                return f"(data->>'{key}' ~* {p})"
        p = next_param(str(val) if isinstance(val, (str, int, float, bool)) else json.dumps(val))
        # Match both scalar equality and array containment (e.g. tags containing a tag)
        return f"(data->>'{key}' = {p}::text OR data->'{key}' @> to_jsonb({p}::text)::jsonb)"

    for key, val in query.items():
        if key == "$or":
            or_parts = []
            for item in val:
                if isinstance(item, dict):
                    sub_conds = [handle_value(k, v) for k, v in item.items()]
                    or_parts.append("(" + " AND ".join(sub_conds) + ")")
            if or_parts:
                conditions.append("(" + " OR ".join(or_parts) + ")")
        else:
            conditions.append(handle_value(key, val))

    where_sql = " AND ".join(conditions) if conditions else "TRUE"
    return where_sql, params


class PostgresDocumentStore(DocumentStore):
    """Document store backed by PostgreSQL (schema app, table documents)."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        schema: str = "app",
    ) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.schema = schema
        self._pool: asyncpg.Pool | None = None
        self._init_done = False

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                min_size=1,
                max_size=10,
                command_timeout=60,
            )
        return self._pool

    async def _ensure_schema(self) -> None:
        if self._init_done:
            return
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.schema}"')
            await conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{self.schema}".documents (
                    collection TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    data JSONB NOT NULL,
                    PRIMARY KEY (collection, entity_id)
                )
                """
            )
        self._init_done = True

    async def create(self, collection: str, document: dict) -> str:
        await self._ensure_schema()
        entity_id = document.get("entity_id") or str(uuid.uuid4())
        doc_copy = {**document, "entity_id": entity_id}
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                f'''
                INSERT INTO "{self.schema}".documents (collection, entity_id, data)
                VALUES ($1, $2, $3::jsonb)
                ON CONFLICT (collection, entity_id) DO UPDATE SET data = $3::jsonb
                ''',
                collection,
                entity_id,
                json.dumps(doc_copy, default=str),
            )
        return entity_id

    async def read(self, collection: str, entity_id: str) -> dict | None:
        await self._ensure_schema()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f'SELECT data FROM "{self.schema}".documents WHERE collection = $1 AND entity_id = $2',
                collection,
                entity_id,
            )
        if row is None:
            return None
        return dict(row["data"])

    async def update(self, collection: str, entity_id: str, document: dict) -> bool:
        await self._ensure_schema()
        doc_copy = {**document, "entity_id": entity_id}
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                f'UPDATE "{self.schema}".documents SET data = $3::jsonb WHERE collection = $1 AND entity_id = $2',
                collection,
                entity_id,
                json.dumps(doc_copy, default=str),
            )
        return result == "UPDATE 1"

    async def delete(self, collection: str, entity_id: str) -> bool:
        await self._ensure_schema()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                f'DELETE FROM "{self.schema}".documents WHERE collection = $1 AND entity_id = $2',
                collection,
                entity_id,
            )
        return result == "DELETE 1"

    async def find(self, collection: str, query: dict) -> list[dict]:
        await self._ensure_schema()
        where_sql, params = _build_where_and_params(query, param_start=2)
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f'SELECT data FROM "{self.schema}".documents WHERE collection = $1 AND {where_sql}',
                collection,
                *params,
            )
        return [dict(r["data"]) for r in rows]

    async def delete_many(self, collection: str) -> int:
        """Delete all documents in a collection (for tests). Returns count deleted."""
        await self._ensure_schema()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                f'DELETE FROM "{self.schema}".documents WHERE collection = $1',
                collection,
            )
        # Result like "DELETE 3"
        return int(result.split()[-1]) if result.startswith("DELETE") else 0

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
        self._init_done = False

import asyncio
import os

import polars as pl

from src.models.tool_response import ToolResponse
from src.storage.backends.dispatcher import get_object_store
from src.storage.backends.postgres_document_store import PostgresDocumentStore
from src.storage.repositories.registry import RepositoryRegistry


async def main():
    """Example usage of the storage system."""

    # 1. Initialize storage backends
    # Postgres for metadata (jobs, notes, tool responses)
    doc_store = PostgresDocumentStore(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "maxa_ds"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        schema=os.getenv("POSTGRES_SCHEMA", "app"),
    )

    # Object store: MinIO (local) or GCS (GCP) - from OBJECT_STORE_BACKEND env
    obj_store = get_object_store()

    # 2. Create repository registry
    registry = RepositoryRegistry(
        document_store=doc_store,
        object_store=obj_store,
    )
    await registry.initialize()

    # 3. Create a tool response with a DataFrame (will be stored in MinIO)
    df = pl.DataFrame(
        {
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
            "score": [85.5, 92.0, 78.5],
        }
    )

    tool_response = ToolResponse(
        payload=df,
        summary="User dataset with names, ages, and scores",
        metadata={"rows": len(df), "columns": len(df.columns)},
    )

    # 4. Save tool response (automatically routes to ToolResponseRepository)
    saved = await registry.save(tool_response)
    print(f"✓ Saved tool response: {saved.entity_id}")

    # 5. Retrieve tool response
    retrieved = await registry.get("tool_response", saved.entity_id)
    print(f"✓ Retrieved tool response: {retrieved.entity_id}")
    print(f"  Summary: {retrieved.summary}")
    print(f"  Payload type: {type(retrieved.payload)}")

    # 6. List all tool responses
    all_responses = await registry.list("tool_response")
    print(f"✓ Found {len(all_responses)} tool responses")

    # 7. Delete tool response
    deleted = await registry.delete("tool_response", saved.entity_id)
    print(f"✓ Deleted tool response: {deleted}")

    await doc_store.close()


if __name__ == "__main__":
    asyncio.run(main())

"""Pytest fixtures for the maxa-ds-agent test suite.

This module provides reusable fixtures for testing storage, MCP tools, and workers.
"""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.tool_response import ToolResponse
from src.storage.backends.postgres_document_store import PostgresDocumentStore
from src.storage.backends.object_store import MinIOObjectStore
from src.storage.repositories.registry import RepositoryRegistry, set_repository_registry


# =============================================================================
# Event Loop Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Environment Fixtures
# =============================================================================


@pytest.fixture(scope="session", autouse=True)
def setup_test_env() -> None:
    """Set up test environment variables."""
    os.environ.setdefault("POSTGRES_HOST", "localhost")
    os.environ.setdefault("POSTGRES_PORT", "5432")
    os.environ.setdefault("POSTGRES_DB", "test_maxa_ds")
    os.environ.setdefault("POSTGRES_USER", "postgres")
    os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
    os.environ.setdefault("POSTGRES_SCHEMA", "app")
    os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
    os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
    os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


# =============================================================================
# Mock Storage Fixtures (No external dependencies)
# =============================================================================


@pytest.fixture
def mock_document_store() -> MagicMock:
    """Create a mock document store for unit tests."""
    store = MagicMock()
    store.create = AsyncMock(return_value=True)
    store.read = AsyncMock(return_value=None)
    store.update = AsyncMock(return_value=True)
    store.delete = AsyncMock(return_value=True)
    store.find = AsyncMock(return_value=[])
    return store


@pytest.fixture
def mock_object_store() -> MagicMock:
    """Create a mock object store for unit tests."""
    store = MagicMock()
    store.put = AsyncMock(return_value=True)
    store.get = AsyncMock(return_value=None)
    store.delete = AsyncMock(return_value=True)
    store.exists = AsyncMock(return_value=False)
    return store


@pytest.fixture
async def mock_registry(
    mock_document_store: MagicMock,
    mock_object_store: MagicMock,
) -> AsyncGenerator[RepositoryRegistry, None]:
    """Create a mock repository registry for unit tests."""
    registry = RepositoryRegistry(
        document_store=mock_document_store,
        object_store=mock_object_store,
    )
    await registry.initialize()
    yield registry


# =============================================================================
# Integration Test Fixtures (Require running services)
# =============================================================================


@pytest.fixture
async def doc_store() -> AsyncGenerator[PostgresDocumentStore, None]:
    """Document store for integration testing.

    Requires Postgres to be running (e.g. localhost with test_maxa_ds database).
    """
    store = PostgresDocumentStore(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "test_maxa_ds"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        schema=os.getenv("POSTGRES_SCHEMA", "app"),
    )
    yield store
    await store.close()


@pytest.fixture
async def obj_store() -> MinIOObjectStore:
    """Object store for integration testing.

    Requires MinIO to be running on localhost:9000.
    """
    return MinIOObjectStore(
        endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        secure=False,
    )


@pytest.fixture
async def registry(
    doc_store: PostgresDocumentStore,
    obj_store: MinIOObjectStore,
) -> AsyncGenerator[RepositoryRegistry, None]:
    """Repository registry for integration testing."""
    reg = RepositoryRegistry(
        document_store=doc_store,
        object_store=obj_store,
    )
    await reg.initialize()
    yield reg


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_tool_response() -> ToolResponse:
    """Create a sample ToolResponse for testing."""
    return ToolResponse(
        payload={"data": [1, 2, 3, 4, 5]},
        summary="Sample data with 5 integers",
        metadata={"tool": "test_tool", "version": 1},
        storage_hint="always",
        suggested_name="test_data",
    )


@pytest.fixture
def sample_dataframe_payload() -> dict[str, Any]:
    """Create a sample DataFrame-like payload for testing."""
    return {
        "columns": ["id", "name", "value"],
        "data": [
            [1, "Alice", 100],
            [2, "Bob", 200],
            [3, "Charlie", 300],
        ],
    }


# =============================================================================
# Cleanup Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
async def cleanup_test_data(request: pytest.FixtureRequest) -> AsyncGenerator[None, None]:
    """Clean up test data after each test (integration tests only)."""
    yield
    try:
        doc_store = request.getfixturevalue("doc_store")
        await doc_store.delete_many("tool_responses")
        await doc_store.delete_many("jobs")
        await doc_store.delete_many("notes")
    except Exception:
        pass  # doc_store not requested or cleanup failed


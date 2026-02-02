"""Integration tests for storage layer.

These tests require Postgres and MinIO to be running.
"""

import pytest

from src.models.tool_response import ToolResponse


@pytest.mark.integration
class TestStorageIntegration:
    """Integration tests for storage backends."""

    @pytest.mark.asyncio
    async def test_save_and_retrieve_tool_response(self, registry) -> None:
        """Test saving and retrieving a ToolResponse."""
        tr = ToolResponse(
            payload={"test": "data"},
            summary="Integration test",
            metadata={},
            storage_hint="always",
        )

        # Save
        saved = await registry.save(tr)
        assert saved.entity_id == tr.entity_id

        # Retrieve
        retrieved = await registry.get("tool_response", tr.entity_id)
        assert retrieved is not None
        assert retrieved.entity_id == tr.entity_id
        assert retrieved.summary == "Integration test"

    @pytest.mark.asyncio
    async def test_list_tool_responses(self, registry) -> None:
        """Test listing tool responses with filters."""
        # Create multiple responses
        tr1 = ToolResponse(
            payload={"id": 1},
            summary="First",
            metadata={"type": "test"},
            storage_hint="always",
        )
        tr2 = ToolResponse(
            payload={"id": 2},
            summary="Second",
            metadata={"type": "test"},
            storage_hint="always",
        )

        await registry.save(tr1)
        await registry.save(tr2)

        # List all
        results = await registry.list("tool_response")
        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_delete_tool_response(self, registry) -> None:
        """Test deleting a tool response."""
        tr = ToolResponse(
            payload={"delete": "me"},
            summary="To be deleted",
            metadata={},
            storage_hint="always",
        )

        await registry.save(tr)

        # Verify it exists
        exists = await registry.get("tool_response", tr.entity_id)
        assert exists is not None

        # Delete
        deleted = await registry.delete("tool_response", tr.entity_id)
        assert deleted is True

        # Verify deletion
        gone = await registry.get("tool_response", tr.entity_id)
        assert gone is None


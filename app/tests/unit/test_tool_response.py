"""Unit tests for ToolResponse model."""

import pytest

from src.models.tool_response import ToolResponse


@pytest.mark.unit
class TestToolResponse:
    """Tests for ToolResponse model."""

    def test_create_tool_response(self) -> None:
        """Test ToolResponse can be created with required fields."""
        tr = ToolResponse(
            payload={"data": [1, 2, 3]},
            summary="Test summary",
            metadata={},
            storage_hint="never",
        )

        assert tr.entity_id is not None
        assert tr.type == "tool_response"
        assert tr.summary == "Test summary"
        assert tr.payload == {"data": [1, 2, 3]}
        assert tr.storage_hint == "never"
        assert tr.version == 1

    def test_entity_id_is_unique(self) -> None:
        """Test each ToolResponse gets a unique entity_id."""
        tr1 = ToolResponse(payload=None, summary="First", metadata={})
        tr2 = ToolResponse(payload=None, summary="Second", metadata={})

        assert tr1.entity_id != tr2.entity_id

    def test_to_dict(self) -> None:
        """Test ToolResponse can be serialized to dict."""
        tr = ToolResponse(
            payload={"key": "value"},
            summary="Serialization test",
            metadata={"tool": "test"},
            storage_hint="always",
            suggested_name="test_var",
        )

        result = tr.to_dict()

        assert result["payload"] == {"key": "value"}
        assert result["summary"] == "Serialization test"
        assert result["metadata"] == {"tool": "test"}
        assert result["storage_hint"] == "always"
        assert result["suggested_name"] == "test_var"

    def test_from_dict(self) -> None:
        """Test ToolResponse can be deserialized from dict."""
        data = {
            "payload": {"data": [1, 2, 3]},
            "summary": "From dict test",
            "metadata": {"source": "test"},
            "storage_hint": "always",
            "suggested_name": "from_dict_var",
        }

        tr = ToolResponse.from_dict(data)

        assert tr.payload == {"data": [1, 2, 3]}
        assert tr.summary == "From dict test"
        assert tr.metadata == {"source": "test"}
        assert tr.storage_hint == "always"
        assert tr.suggested_name == "from_dict_var"

    def test_to_json_and_from_json(self) -> None:
        """Test ToolResponse JSON serialization roundtrip."""
        original = ToolResponse(
            payload={"nested": {"data": [1, 2, 3]}},
            summary="JSON roundtrip test",
            metadata={"test": True},
            storage_hint="always",
        )

        json_str = original.to_json()
        restored = ToolResponse.from_json(json_str)

        assert restored.payload == original.payload
        assert restored.summary == original.summary
        assert restored.metadata == original.metadata
        assert restored.storage_hint == original.storage_hint

    def test_default_storage_hint(self) -> None:
        """Test default storage_hint is 'auto'."""
        tr = ToolResponse(
            payload=None,
            summary="Default hint test",
            metadata={},
        )

        assert tr.storage_hint == "auto"

    def test_none_payload(self) -> None:
        """Test ToolResponse handles None payload."""
        tr = ToolResponse(
            payload=None,
            summary="Null payload test",
            metadata={"error": True},
            storage_hint="never",
        )

        assert tr.payload is None
        assert tr.to_dict()["payload"] is None


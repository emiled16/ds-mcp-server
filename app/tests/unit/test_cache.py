"""Unit tests for the caching module."""

import pytest

from src.utils.cache import ToolCache


@pytest.mark.unit
class TestToolCache:
    """Tests for ToolCache."""

    def test_hash_call_deterministic(self) -> None:
        """Test that hash_call produces consistent hashes."""
        cache = ToolCache()

        hash1 = cache._hash_call("test_func", (1, 2), {"a": "b"})
        hash2 = cache._hash_call("test_func", (1, 2), {"a": "b"})

        assert hash1 == hash2

    def test_hash_call_different_for_different_inputs(self) -> None:
        """Test that different inputs produce different hashes."""
        cache = ToolCache()

        hash1 = cache._hash_call("test_func", (1, 2), {"a": "b"})
        hash2 = cache._hash_call("test_func", (1, 3), {"a": "b"})
        hash3 = cache._hash_call("other_func", (1, 2), {"a": "b"})

        assert hash1 != hash2
        assert hash1 != hash3
        assert hash2 != hash3

    def test_hash_call_ignores_resolved_kwargs(self) -> None:
        """Test that _resolved_ kwargs are filtered out."""
        cache = ToolCache()

        hash1 = cache._hash_call("test_func", (), {"entity_id": "abc"})
        hash2 = cache._hash_call("test_func", (), {"entity_id": "abc", "_resolved_entity_id": {}})

        assert hash1 == hash2

    def test_hash_call_order_independent_kwargs(self) -> None:
        """Test that kwargs order doesn't affect hash."""
        cache = ToolCache()

        hash1 = cache._hash_call("test_func", (), {"a": 1, "b": 2})
        hash2 = cache._hash_call("test_func", (), {"b": 2, "a": 1})

        assert hash1 == hash2


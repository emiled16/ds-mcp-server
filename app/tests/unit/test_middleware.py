"""Unit tests for MCP middleware."""

import pytest

from src.mcp.middleware import process_tool
from src.models.tool_response import ToolResponse


@pytest.mark.unit
class TestProcessToolDecorator:
    """Tests for the @process_tool decorator."""

    @pytest.mark.asyncio
    async def test_process_tool_returns_summary(self) -> None:
        """Test that decorated tool returns only the summary."""

        @process_tool
        async def sample_tool() -> ToolResponse:
            return ToolResponse(
                payload={"large": "data"},
                summary="Summary only",
                metadata={},
                storage_hint="never",
            )

        result = await sample_tool()

        assert result == "Summary only"
        assert "large" not in str(result)

    @pytest.mark.asyncio
    async def test_process_tool_handles_sync_function(self) -> None:
        """Test that decorator handles sync functions."""

        @process_tool
        def sync_tool() -> ToolResponse:
            return ToolResponse(
                payload=None,
                summary="Sync tool result",
                metadata={},
                storage_hint="never",
            )

        result = await sync_tool()

        assert result == "Sync tool result"

    @pytest.mark.asyncio
    async def test_process_tool_handles_exception(self) -> None:
        """Test that decorator handles exceptions gracefully."""

        @process_tool
        async def failing_tool() -> ToolResponse:
            raise ValueError("Something went wrong")

        result = await failing_tool()

        assert "Error in tool failing_tool" in result
        assert "Something went wrong" in result

    @pytest.mark.asyncio
    async def test_process_tool_preserves_function_name(self) -> None:
        """Test that decorator preserves the original function name."""

        @process_tool
        async def named_tool() -> ToolResponse:
            return ToolResponse(
                payload=None,
                summary="Named tool",
                metadata={},
                storage_hint="never",
            )

        assert named_tool.__name__ == "named_tool"

    @pytest.mark.asyncio
    async def test_process_tool_with_arguments(self) -> None:
        """Test that decorator passes arguments correctly."""

        @process_tool
        async def tool_with_args(x: int, y: str, z: bool = False) -> ToolResponse:
            return ToolResponse(
                payload={"x": x, "y": y, "z": z},
                summary=f"Args: x={x}, y={y}, z={z}",
                metadata={},
                storage_hint="never",
            )

        result = await tool_with_args(42, "hello", z=True)

        assert "x=42" in result
        assert "y=hello" in result
        assert "z=True" in result


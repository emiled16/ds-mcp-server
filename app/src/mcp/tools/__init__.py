"""MCP tools package.

This module provides a registry of all available tools for dynamic lookup.
"""

from collections.abc import Callable
from typing import Any

# Registry of tool functions by name
_tool_registry: dict[str, Callable] = {}


def register_tool(func: Callable) -> Callable:
    """Register a tool function in the global registry."""
    _tool_registry[func.__name__] = func
    return func


def get_tool_function(name: str) -> Callable | None:
    """Get a tool function by name."""
    return _tool_registry.get(name)


def list_tool_names() -> list[str]:
    """List all registered tool names."""
    return list(_tool_registry.keys())


def get_all_tools() -> dict[str, Callable]:
    """Get all registered tools."""
    return _tool_registry.copy()

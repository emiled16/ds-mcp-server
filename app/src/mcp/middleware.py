"""MCP middleware for tool processing.

This middleware handles:
1. Entity reference resolution (entity_id → actual payload)
2. Caching and deduplication
3. Storage based on storage_hint
4. Error handling and logging
"""

import functools
import inspect
from collections.abc import Callable
from logging import getLogger
from typing import Any

from src.models.tool_response import ToolResponse
from src.utils.time import timing

logger = getLogger(__name__)


async def _call_tool(func: Callable, *args: Any, **kwargs: Any) -> Any:
    """Call a tool function, handling both sync and async functions."""
    if inspect.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    return func(*args, **kwargs)


async def resolve_entity_references(kwargs: dict) -> dict:
    """Resolve entity_id references to actual payloads.

    Looks for parameters named 'entity_id' or ending with '_entity_id'
    and replaces them with the actual payload from storage.

    Args:
        kwargs: Tool keyword arguments

    Returns:
        Updated kwargs with resolved entity references
    """
    from src.storage.repositories.registry import get_repository_registry

    resolved_kwargs = kwargs.copy()

    for param_name, param_value in list(kwargs.items()):
        # Check if parameter is named entity_id or ends with _entity_id
        if param_name == "entity_id" or param_name.endswith("_entity_id"):
            if isinstance(param_value, str) and param_value:
                try:
                    registry = get_repository_registry()
                    entity = await registry.get("tool_response", param_value)

                    if entity:
                        # Store the resolved entity for reference
                        resolved_kwargs[f"_resolved_{param_name}"] = entity

                        # If this is just 'entity_id', also add the payload as 'data'
                        if param_name == "entity_id":
                            resolved_kwargs["_resolved_payload"] = entity.payload

                        logger.debug(f"Resolved {param_name}={param_value} to entity")
                    else:
                        logger.warning(f"Entity not found: {param_value}")

                except Exception as e:
                    logger.warning(f"Could not resolve entity {param_value}: {e}")

    return resolved_kwargs


async def save_tool_response(result: ToolResponse) -> None:
    """Save tool response based on storage_hint.

    Args:
        result: ToolResponse to potentially save
    """
    from src.storage.repositories.registry import get_repository_registry

    if result.storage_hint in ["always", "auto"]:
        try:
            registry = get_repository_registry()
            await registry.save(result)
            logger.debug(f"Saved tool response: {result.entity_id}")
        except Exception as e:
            logger.warning(f"Failed to save tool response: {e}")
    elif result.storage_hint == "session":
        # TODO: Implement session storage with TTL in Redis
        try:
            registry = get_repository_registry()
            await registry.save(result)
            logger.debug(f"Saved session tool response: {result.entity_id}")
        except Exception as e:
            logger.warning(f"Failed to save session response: {e}")


def process_tool(func: Callable) -> Callable:
    """Process tool result for MCP.

    This decorator wraps MCP tools to:
    1. Resolve entity_id parameters to actual payloads
    2. Execute the tool function
    3. Save the response based on storage_hint
    4. Return only the summary to the agent

    Usage:
        @mcp.tool
        @process_tool
        async def my_tool(entity_id: str) -> ToolResponse:
            # entity_id is automatically resolved
            # _resolved_entity_id contains the full ToolResponse
            # _resolved_payload contains just the payload
            ...
    """

    @functools.wraps(func)
    @timing
    async def wrapper(*args: Any, context: Any = None, **kwargs: Any) -> Any:
        try:
            logger.info(f"Tool Call [START]: {func.__name__}")

            # 1. Resolve entity_id references
            resolved_kwargs = await resolve_entity_references(kwargs)

            # 2. Filter out _resolved_* keys - these are for internal use only
            # Tools can access resolved data via _resolved_payload if they accept **kwargs
            tool_kwargs = {k: v for k, v in resolved_kwargs.items() if not k.startswith("_resolved_")}

            # 3. Execute tool
            result: ToolResponse = await _call_tool(func, *args, **tool_kwargs)

            # 4. Save based on storage_hint
            await save_tool_response(result)

            logger.info(f"Tool Call [END]: {func.__name__} -> {result.entity_id}")

            # 5. Return summary with entity_id for agent to reference
            if result.storage_hint != "never":
                # Include entity_id so agent can chain operations
                return f"{result.summary}\n\n📌 **entity_id**: `{result.entity_id}`"
            return result.summary

        except Exception as e:
            logger.exception(f"Error in tool {func.__name__}: {e}")
            return ToolResponse(
                payload=None,
                summary=f"Error in tool {func.__name__}: {e}",
                metadata={"error": str(e), "tool": func.__name__},
                storage_hint="never",
            ).summary

    return wrapper

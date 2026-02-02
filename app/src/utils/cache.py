"""Tool caching utilities using Redis.

This module provides caching for MCP tool calls to avoid duplicate executions.
"""

import hashlib
import json
import os

from loguru import logger
from redis.asyncio import Redis

# Default TTL for cached results (1 hour)
DEFAULT_CACHE_TTL = 3600


class ToolCache:
    """Redis-based cache for tool call results.

    Implements deduplication by hashing tool calls and storing results.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        """Initialize the cache.

        Args:
            redis_url: Redis connection URL. Defaults to REDIS_URL env var.
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis: Redis | None = None

    async def _get_client(self) -> Redis:
        """Get or create Redis client."""
        if self._redis is None:
            self._redis = Redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    def _hash_call(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate deterministic hash for a tool call.

        Args:
            func_name: Name of the tool function
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            SHA256 hash of the call signature
        """
        # Filter out internal/resolved kwargs that shouldn't affect caching
        filtered_kwargs = {k: v for k, v in kwargs.items() if not k.startswith("_resolved_")}

        call_data = {
            "func": func_name,
            "args": args,
            "kwargs": sorted(filtered_kwargs.items()),
        }
        call_str = json.dumps(call_data, sort_keys=True, default=str)
        return hashlib.sha256(call_str.encode()).hexdigest()

    async def get(self, func_name: str, args: tuple, kwargs: dict) -> str | None:
        """Get cached result if it exists.

        Args:
            func_name: Name of the tool function
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Cached result or None if not found
        """
        try:
            client = await self._get_client()
            cache_key = f"tool_cache:{self._hash_call(func_name, args, kwargs)}"
            result = await client.get(cache_key)

            if result:
                logger.debug(f"Cache hit for {func_name}")
                return result

            return None

        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    async def set(
        self,
        func_name: str,
        args: tuple,
        kwargs: dict,
        result: str,
        ttl: int = DEFAULT_CACHE_TTL,
    ) -> bool:
        """Cache a tool result.

        Args:
            func_name: Name of the tool function
            args: Positional arguments
            kwargs: Keyword arguments
            result: Result to cache (summary string)
            ttl: Time-to-live in seconds

        Returns:
            True if cached successfully
        """
        try:
            client = await self._get_client()
            cache_key = f"tool_cache:{self._hash_call(func_name, args, kwargs)}"
            await client.setex(cache_key, ttl, result)
            logger.debug(f"Cached result for {func_name}")
            return True

        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False

    async def invalidate(self, pattern: str = "*") -> int:
        """Invalidate cache entries matching pattern.

        Args:
            pattern: Glob pattern to match (default: all entries)

        Returns:
            Number of entries deleted
        """
        try:
            client = await self._get_client()
            deleted = 0
            async for key in client.scan_iter(match=f"tool_cache:{pattern}"):
                await client.delete(key)
                deleted += 1
            logger.info(f"Invalidated {deleted} cache entries")
            return deleted

        except Exception as e:
            logger.warning(f"Cache invalidate error: {e}")
            return 0

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# Module-level cache instance (singleton)
_cache: ToolCache | None = None


def get_cache() -> ToolCache:
    """Get the global cache instance."""
    global _cache  # noqa: PLW0603
    if _cache is None:
        _cache = ToolCache()
    return _cache


async def close_cache() -> None:
    """Close the global cache instance."""
    global _cache  # noqa: PLW0603
    if _cache:
        await _cache.close()
        _cache = None

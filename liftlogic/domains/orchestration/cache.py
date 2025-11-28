"""
Response Cache - In-memory caching with TTL support.

Provides efficient caching for repeated queries to reduce
LLM calls and improve response times.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Any

from .models import CachedResponse, QueryType

logger = logging.getLogger(__name__)

__all__ = ["ResponseCacheImpl"]


class ResponseCacheImpl:
    """
    In-memory response cache with TTL.

    Features:
    - Automatic TTL expiration
    - Pattern-based invalidation
    - Hit tracking for analytics
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600) -> None:
        """
        Initialize cache.

        Args:
            max_size: Maximum number of cached entries
            default_ttl: Default TTL in seconds
        """
        self._cache: dict[str, CachedResponse] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl

    async def get(self, key: str) -> CachedResponse | None:
        """Get cached response if not expired."""
        entry = self._cache.get(key)
        if not entry:
            return None

        # Check expiration
        if entry.expires_at and datetime.utcnow() > entry.expires_at:
            del self._cache[key]
            logger.debug("Cache entry expired: %s", key[:16])
            return None

        # Update hit count
        entry.hit_count += 1
        logger.debug("Cache hit: %s (hits: %d)", key[:16], entry.hit_count)
        return entry

    async def set(
        self,
        key: str,
        response: Any,
        ttl_seconds: int | None = None,
        query_type: QueryType = QueryType.UNKNOWN,
    ) -> None:
        """Cache a response."""
        # Enforce max size with LRU eviction
        if len(self._cache) >= self._max_size:
            await self._evict_oldest()

        ttl = ttl_seconds or self._default_ttl
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)

        self._cache[key] = CachedResponse(
            key=key,
            response=response,
            query_type=query_type,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            hit_count=0,
        )

        logger.debug("Cached response: %s (TTL: %ds)", key[:16], ttl)

    async def invalidate(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        regex = re.compile(pattern)
        keys_to_delete = [k for k in self._cache if regex.search(k)]

        for key in keys_to_delete:
            del self._cache[key]

        logger.info("Invalidated %d cache entries matching: %s", len(keys_to_delete), pattern)
        return len(keys_to_delete)

    async def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        logger.info("Cleared %d cache entries", count)

    async def _evict_oldest(self) -> None:
        """Evict oldest entries to make room."""
        if not self._cache:
            return

        # Sort by creation time and remove oldest 10%
        sorted_keys = sorted(
            self._cache.keys(),
            key=lambda k: self._cache[k].created_at,
        )
        evict_count = max(1, len(sorted_keys) // 10)

        for key in sorted_keys[:evict_count]:
            del self._cache[key]

        logger.debug("Evicted %d oldest cache entries", evict_count)

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_hits = sum(e.hit_count for e in self._cache.values())
        by_type: dict[str, int] = {}
        for entry in self._cache.values():
            type_name = entry.query_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "total_hits": total_hits,
            "by_type": by_type,
        }

    @staticmethod
    def generate_key(query: str, context: dict[str, Any] | None = None) -> str:
        """Generate cache key from query and context."""
        # Normalize query
        normalized = query.lower().strip()

        # Include relevant context in key
        key_parts = [normalized]
        if context:
            for k in sorted(context.keys()):
                if k in ("manufacturer", "model", "session_id"):
                    key_parts.append(f"{k}:{context[k]}")

        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]

"""
Orchestration Contracts - Interfaces for orchestration domain.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .models import CachedResponse, PipelineResult, Query, RoutingDecision


@runtime_checkable
class QueryRouter(Protocol):
    """Contract for query routing."""

    async def route(self, query: Query) -> RoutingDecision:
        """
        Determine how to route a query.

        Args:
            query: The incoming query

        Returns:
            Routing decision with model/pipeline selection
        """
        ...

    async def classify_query(self, query: Query) -> str:
        """
        Classify query type.

        Args:
            query: The incoming query

        Returns:
            Query type classification
        """
        ...


@runtime_checkable
class ResponseCache(Protocol):
    """Contract for response caching."""

    async def get(self, key: str) -> CachedResponse | None:
        """Get cached response."""
        ...

    async def set(
        self,
        key: str,
        response: Any,
        ttl_seconds: int = 3600,
    ) -> None:
        """Cache a response."""
        ...

    async def invalidate(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        ...


@runtime_checkable
class PipelineOrchestrator(Protocol):
    """Contract for query pipeline orchestration."""

    async def execute(self, query: Query) -> PipelineResult:
        """
        Execute query through appropriate pipeline.

        Args:
            query: The incoming query

        Returns:
            Pipeline execution result
        """
        ...

    async def execute_with_context(
        self,
        query: Query,
        context: dict,
    ) -> PipelineResult:
        """
        Execute query with additional context.

        Args:
            query: The incoming query
            context: Additional context (conversation history, etc.)

        Returns:
            Pipeline execution result
        """
        ...

"""
Search Contracts - Interfaces for search domain.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import SearchQuery, SearchResult, RankedResult


@runtime_checkable
class SearchEngine(Protocol):
    """Contract for search implementations."""

    async def search(
        self,
        query: SearchQuery,
    ) -> list[SearchResult]:
        """Execute search and return results."""
        ...


@runtime_checkable
class Ranker(Protocol):
    """Contract for result ranking implementations."""

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
    ) -> list[RankedResult]:
        """Rerank search results."""
        ...

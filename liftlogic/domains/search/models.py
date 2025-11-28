"""
Search Models - Data types for search domain.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Search request."""

    query: str = Field(..., min_length=1)
    limit: int = Field(default=20, ge=1, le=100)
    manufacturer: str | None = None
    document_type: str | None = None
    use_vector: bool = True
    use_keyword: bool = True
    use_reranking: bool = True

    model_config = {"frozen": True}


class SearchResult(BaseModel):
    """Single search result."""

    doc_id: int
    filename: str
    content: str
    manufacturer: str | None = None
    document_type: str | None = None
    score: float = 0.0
    source: str = "unknown"  # "vector", "keyword", "hybrid"
    metadata: dict[str, Any] = Field(default_factory=dict)


class RankedResult(BaseModel):
    """Reranked search result with additional scoring."""

    result: SearchResult
    original_rank: int
    reranked_score: float
    final_rank: int


class RAGResponse(BaseModel):
    """RAG-generated answer with citations."""

    answer: str
    sources: list[SearchResult]
    confidence: float = 0.0
    model_used: str = ""

"""
Search Domain - Hybrid search with RAG capabilities.

This domain handles:
- Vector similarity search (FAISS)
- Keyword search (SQLite FTS5)
- Reciprocal Rank Fusion
- Query expansion
- RAG answer generation
"""

from .contracts import SearchEngine, Ranker
from .models import SearchQuery, SearchResult, RankedResult
from .hybrid_search import HybridSearchEngine

__all__ = [
    "SearchEngine",
    "Ranker",
    "SearchQuery",
    "SearchResult",
    "RankedResult",
    "HybridSearchEngine",
]

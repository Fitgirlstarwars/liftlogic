"""
Search Domain - Hybrid search with RAG capabilities.

This domain handles:
- Vector similarity search (FAISS)
- Keyword search (SQLite FTS5)
- Reciprocal Rank Fusion
- Query expansion
- RAG answer generation
"""

from .contracts import Ranker, SearchEngine
from .hybrid_search import HybridSearchEngine
from .models import RankedResult, SearchQuery, SearchResult

__all__ = [
    "SearchEngine",
    "Ranker",
    "SearchQuery",
    "SearchResult",
    "RankedResult",
    "HybridSearchEngine",
]

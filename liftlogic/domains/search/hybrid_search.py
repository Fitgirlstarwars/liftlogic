"""
Hybrid Search Engine - Combines vector and keyword search with RRF.

Features:
- FAISS vector similarity search
- SQLite FTS5 keyword search
- Reciprocal Rank Fusion (RRF)
- Optional cross-encoder reranking
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sentence_transformers import SentenceTransformer

from .models import RankedResult, SearchQuery, SearchResult

if TYPE_CHECKING:
    from liftlogic.adapters.faiss import FAISSIndex
    from liftlogic.adapters.sqlite import SQLiteRepository

logger = logging.getLogger(__name__)

__all__ = ["HybridSearchEngine"]


class HybridSearchEngine:
    """
    Hybrid search combining vector and keyword approaches.

    Example:
        >>> engine = HybridSearchEngine(faiss_index, sqlite_repo)
        >>> results = await engine.search(SearchQuery(query="fault 505"))
    """

    def __init__(
        self,
        faiss_index: FAISSIndex,
        sqlite_repo: SQLiteRepository,
        embedding_model: str = "all-MiniLM-L6-v2",
        rrf_k: int = 60,
    ) -> None:
        """
        Initialize hybrid search engine.

        Args:
            faiss_index: FAISS vector index
            sqlite_repo: SQLite repository with FTS
            embedding_model: Sentence transformer model name
            rrf_k: RRF constant (default 60)
        """
        self._faiss = faiss_index
        self._sqlite = sqlite_repo
        self._rrf_k = rrf_k

        # Load embedding model
        self._embedder = SentenceTransformer(embedding_model)

    async def search(self, query: SearchQuery) -> list[SearchResult]:
        """
        Execute hybrid search.

        Args:
            query: Search query parameters

        Returns:
            List of search results sorted by relevance
        """
        results_map: dict[int, SearchResult] = {}
        vector_ranks: dict[int, int] = {}
        keyword_ranks: dict[int, int] = {}

        # Vector search
        if query.use_vector and self._faiss.size > 0:
            vector_results = await self._vector_search(query)
            for rank, result in enumerate(vector_results, 1):
                results_map[result.doc_id] = result
                vector_ranks[result.doc_id] = rank

        # Keyword search
        if query.use_keyword:
            keyword_results = await self._keyword_search(query)
            for rank, result in enumerate(keyword_results, 1):
                if result.doc_id not in results_map:
                    results_map[result.doc_id] = result
                keyword_ranks[result.doc_id] = rank

        # Reciprocal Rank Fusion
        rrf_scores: dict[int, float] = {}
        for doc_id in results_map:
            score = 0.0
            if doc_id in vector_ranks:
                score += 1.0 / (self._rrf_k + vector_ranks[doc_id])
            if doc_id in keyword_ranks:
                score += 1.0 / (self._rrf_k + keyword_ranks[doc_id])
            rrf_scores[doc_id] = score

        # Sort by RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        results = []
        for doc_id in sorted_ids[: query.limit]:
            result = results_map[doc_id]
            result.score = rrf_scores[doc_id]
            result.source = "hybrid"
            results.append(result)

        logger.info(
            "Hybrid search: query='%s' -> %d results (vector=%d, keyword=%d)",
            query.query[:50],
            len(results),
            len(vector_ranks),
            len(keyword_ranks),
        )

        return results

    async def _vector_search(self, query: SearchQuery) -> list[SearchResult]:
        """Execute vector similarity search."""
        # Generate embedding
        embedding = self._embedder.encode(query.query)

        # Search FAISS
        faiss_results = await self._faiss.search(embedding, k=query.limit * 2)

        results = []
        for item in faiss_results:
            meta = item["metadata"]
            results.append(
                SearchResult(
                    doc_id=meta.get("doc_id", 0),
                    filename=meta.get("filename", ""),
                    content=meta.get("content", "")[:500],
                    manufacturer=meta.get("manufacturer"),
                    document_type=meta.get("document_type"),
                    score=item["score"],
                    source="vector",
                )
            )

        return results

    async def _keyword_search(self, query: SearchQuery) -> list[SearchResult]:
        """Execute keyword search via FTS5."""
        rows = await self._sqlite.search_fts(
            query=query.query,
            limit=query.limit * 2,
            manufacturer=query.manufacturer,
        )

        results = []
        for row in rows:
            results.append(
                SearchResult(
                    doc_id=row["id"],
                    filename=row["filename"],
                    content=(row.get("content") or "")[:500],
                    manufacturer=row.get("manufacturer"),
                    document_type=row.get("document_type"),
                    score=abs(row.get("score", 0)),  # BM25 scores are negative
                    source="keyword",
                )
            )

        return results

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int = 10,
    ) -> list[RankedResult]:
        """
        Rerank results using cross-encoder (if available).

        Args:
            query: Original query
            results: Results to rerank
            top_k: Number of results to return

        Returns:
            Reranked results
        """
        # For now, return as-is with rank info
        # TODO: Add cross-encoder reranking
        ranked = []
        for i, result in enumerate(results[:top_k]):
            ranked.append(
                RankedResult(
                    result=result,
                    original_rank=i + 1,
                    reranked_score=result.score,
                    final_rank=i + 1,
                )
            )
        return ranked

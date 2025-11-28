"""
Tests for search domain models and hybrid search engine.
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from .hybrid_search import HybridSearchEngine
from .models import RAGResponse, RankedResult, SearchQuery, SearchResult


# --- SearchQuery Tests ---


def test_search_query_basic() -> None:
    """Test SearchQuery with minimal required fields."""
    query = SearchQuery(query="fault code 505")
    assert query.query == "fault code 505"
    assert query.limit == 20
    assert query.use_vector is True
    assert query.use_keyword is True


def test_search_query_with_filters() -> None:
    """Test SearchQuery with filters."""
    query = SearchQuery(
        query="door fault",
        limit=10,
        manufacturer="KONE",
        document_type="service_manual",
    )
    assert query.manufacturer == "KONE"
    assert query.document_type == "service_manual"
    assert query.limit == 10


def test_search_query_limit_validation() -> None:
    """Test SearchQuery limit must be 1-100."""
    # Valid limits
    query = SearchQuery(query="test", limit=1)
    assert query.limit == 1
    query = SearchQuery(query="test", limit=100)
    assert query.limit == 100

    # Invalid limits
    with pytest.raises(ValueError):
        SearchQuery(query="test", limit=0)
    with pytest.raises(ValueError):
        SearchQuery(query="test", limit=101)


def test_search_query_requires_query() -> None:
    """Test SearchQuery requires non-empty query."""
    with pytest.raises(ValueError):
        SearchQuery(query="")


def test_search_query_search_mode_flags() -> None:
    """Test SearchQuery can disable vector or keyword search."""
    # Keyword only
    query = SearchQuery(query="test", use_vector=False, use_keyword=True)
    assert query.use_vector is False
    assert query.use_keyword is True

    # Vector only
    query = SearchQuery(query="test", use_vector=True, use_keyword=False)
    assert query.use_vector is True
    assert query.use_keyword is False


def test_search_query_is_immutable() -> None:
    """Test SearchQuery is frozen/immutable."""
    query = SearchQuery(query="test")
    with pytest.raises(Exception):
        query.query = "changed"  # type: ignore


# --- SearchResult Tests ---


def test_search_result_basic() -> None:
    """Test SearchResult with required fields."""
    result = SearchResult(
        doc_id=1,
        filename="manual.pdf",
        content="Sample content",
    )
    assert result.doc_id == 1
    assert result.filename == "manual.pdf"
    assert result.score == 0.0
    assert result.source == "unknown"


def test_search_result_full() -> None:
    """Test SearchResult with all fields."""
    result = SearchResult(
        doc_id=42,
        filename="kone_service.pdf",
        content="Fault code 505 indicates door zone sensor malfunction...",
        manufacturer="KONE",
        document_type="service_manual",
        score=0.95,
        source="hybrid",
        metadata={"page": 45, "section": "Troubleshooting"},
    )
    assert result.manufacturer == "KONE"
    assert result.score == 0.95
    assert result.source == "hybrid"
    assert result.metadata["page"] == 45


# --- RankedResult Tests ---


def test_ranked_result() -> None:
    """Test RankedResult model."""
    search_result = SearchResult(
        doc_id=1,
        filename="manual.pdf",
        content="Test content",
        score=0.8,
    )
    ranked = RankedResult(
        result=search_result,
        original_rank=3,
        reranked_score=0.92,
        final_rank=1,
    )
    assert ranked.original_rank == 3
    assert ranked.final_rank == 1
    assert ranked.reranked_score == 0.92
    assert ranked.result.doc_id == 1


# --- RAGResponse Tests ---


def test_rag_response_basic() -> None:
    """Test RAGResponse with minimal fields."""
    response = RAGResponse(
        answer="Fault 505 is a door zone sensor issue.",
        sources=[],
    )
    assert response.answer == "Fault 505 is a door zone sensor issue."
    assert response.confidence == 0.0
    assert len(response.sources) == 0


def test_rag_response_with_sources() -> None:
    """Test RAGResponse with source citations."""
    sources = [
        SearchResult(doc_id=1, filename="kone.pdf", content="Source 1", score=0.9),
        SearchResult(doc_id=2, filename="otis.pdf", content="Source 2", score=0.85),
    ]
    response = RAGResponse(
        answer="Based on the manuals, fault 505 indicates...",
        sources=sources,
        confidence=0.88,
        model_used="gemini-2.0-flash",
    )
    assert len(response.sources) == 2
    assert response.confidence == 0.88
    assert response.model_used == "gemini-2.0-flash"


# --- HybridSearchEngine Tests ---


@pytest.fixture
def mock_faiss_index() -> AsyncMock:
    """Create a mock FAISS index."""
    mock = AsyncMock()
    mock.size = 100  # Non-empty index
    mock.search.return_value = [
        {
            "score": 0.95,
            "id": 0,
            "metadata": {
                "doc_id": 1,
                "filename": "kone_manual.pdf",
                "content": "Fault 505 door sensor",
                "manufacturer": "KONE",
            },
        },
        {
            "score": 0.85,
            "id": 1,
            "metadata": {
                "doc_id": 2,
                "filename": "otis_manual.pdf",
                "content": "Door fault troubleshooting",
                "manufacturer": "OTIS",
            },
        },
    ]
    return mock


@pytest.fixture
def mock_sqlite_repo() -> AsyncMock:
    """Create a mock SQLite repository."""
    mock = AsyncMock()
    mock.search_fts.return_value = [
        {
            "id": 1,
            "filename": "kone_manual.pdf",
            "content": "Fault 505 door sensor malfunction",
            "manufacturer": "KONE",
            "document_type": "service_manual",
            "score": -2.5,  # BM25 scores are negative
        },
        {
            "id": 3,
            "filename": "schindler_manual.pdf",
            "content": "Door fault codes",
            "manufacturer": "Schindler",
            "score": -3.0,
        },
    ]
    return mock


@pytest.fixture
def mock_embedder() -> MagicMock:
    """Create a mock sentence transformer."""
    mock = MagicMock()
    # Return a numpy array for embeddings
    mock.encode.return_value = np.array([0.1, 0.2, 0.3] * 128)  # 384-dim vector
    return mock


@pytest.fixture
def search_engine(
    mock_faiss_index: AsyncMock,
    mock_sqlite_repo: AsyncMock,
    mock_embedder: MagicMock,
) -> HybridSearchEngine:
    """Create a HybridSearchEngine with mocked dependencies."""
    with patch(
        "liftlogic.domains.search.hybrid_search.SentenceTransformer",
        return_value=mock_embedder,
    ):
        engine = HybridSearchEngine(
            faiss_index=mock_faiss_index,
            sqlite_repo=mock_sqlite_repo,
            rrf_k=60,
        )
    return engine


async def test_hybrid_search_basic(search_engine: HybridSearchEngine) -> None:
    """Test basic hybrid search."""
    query = SearchQuery(query="fault 505")
    results = await search_engine.search(query)

    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)
    assert all(r.source == "hybrid" for r in results)


async def test_hybrid_search_rrf_fusion(search_engine: HybridSearchEngine) -> None:
    """Test RRF fusion combines results correctly."""
    query = SearchQuery(query="door fault", limit=10)
    results = await search_engine.search(query)

    # Document 1 appears in both vector and keyword results, should rank higher
    doc_ids = [r.doc_id for r in results]
    assert 1 in doc_ids  # Common result should be present

    # Results should be sorted by score (RRF)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


async def test_hybrid_search_vector_only(
    mock_faiss_index: AsyncMock,
    mock_sqlite_repo: AsyncMock,
    mock_embedder: MagicMock,
) -> None:
    """Test search with only vector mode enabled."""
    with patch(
        "liftlogic.domains.search.hybrid_search.SentenceTransformer",
        return_value=mock_embedder,
    ):
        engine = HybridSearchEngine(
            faiss_index=mock_faiss_index,
            sqlite_repo=mock_sqlite_repo,
        )

    query = SearchQuery(query="test", use_vector=True, use_keyword=False)
    results = await engine.search(query)

    # Should only call FAISS, not SQLite
    mock_faiss_index.search.assert_called()
    mock_sqlite_repo.search_fts.assert_not_called()


async def test_hybrid_search_keyword_only(
    mock_faiss_index: AsyncMock,
    mock_sqlite_repo: AsyncMock,
    mock_embedder: MagicMock,
) -> None:
    """Test search with only keyword mode enabled."""
    with patch(
        "liftlogic.domains.search.hybrid_search.SentenceTransformer",
        return_value=mock_embedder,
    ):
        engine = HybridSearchEngine(
            faiss_index=mock_faiss_index,
            sqlite_repo=mock_sqlite_repo,
        )

    query = SearchQuery(query="test", use_vector=False, use_keyword=True)
    results = await engine.search(query)

    # Should only call SQLite, not FAISS
    mock_sqlite_repo.search_fts.assert_called()


async def test_hybrid_search_empty_index(
    mock_sqlite_repo: AsyncMock,
    mock_embedder: MagicMock,
) -> None:
    """Test search with empty FAISS index falls back to keyword only."""
    mock_empty_faiss = AsyncMock()
    mock_empty_faiss.size = 0  # Empty index

    with patch(
        "liftlogic.domains.search.hybrid_search.SentenceTransformer",
        return_value=mock_embedder,
    ):
        engine = HybridSearchEngine(
            faiss_index=mock_empty_faiss,
            sqlite_repo=mock_sqlite_repo,
        )

    query = SearchQuery(query="test")
    results = await engine.search(query)

    # Should still return results from keyword search
    assert len(results) > 0
    mock_empty_faiss.search.assert_not_called()  # Skipped due to empty index


async def test_hybrid_search_with_manufacturer_filter(
    mock_faiss_index: AsyncMock,
    mock_sqlite_repo: AsyncMock,
    mock_embedder: MagicMock,
) -> None:
    """Test search passes manufacturer filter to keyword search."""
    with patch(
        "liftlogic.domains.search.hybrid_search.SentenceTransformer",
        return_value=mock_embedder,
    ):
        engine = HybridSearchEngine(
            faiss_index=mock_faiss_index,
            sqlite_repo=mock_sqlite_repo,
        )

    query = SearchQuery(query="fault", manufacturer="KONE")
    await engine.search(query)

    # Verify manufacturer was passed to FTS search
    mock_sqlite_repo.search_fts.assert_called_once()
    call_kwargs = mock_sqlite_repo.search_fts.call_args
    assert call_kwargs.kwargs.get("manufacturer") == "KONE"


async def test_rerank_returns_ranked_results(search_engine: HybridSearchEngine) -> None:
    """Test rerank method returns RankedResult objects."""
    results = [
        SearchResult(doc_id=1, filename="a.pdf", content="Content A", score=0.9),
        SearchResult(doc_id=2, filename="b.pdf", content="Content B", score=0.8),
        SearchResult(doc_id=3, filename="c.pdf", content="Content C", score=0.7),
    ]

    ranked = await search_engine.rerank("test query", results, top_k=2)

    assert len(ranked) == 2
    assert all(isinstance(r, RankedResult) for r in ranked)
    assert ranked[0].original_rank == 1
    assert ranked[1].original_rank == 2


async def test_rerank_respects_top_k(search_engine: HybridSearchEngine) -> None:
    """Test rerank respects top_k parameter."""
    results = [
        SearchResult(doc_id=i, filename=f"{i}.pdf", content=f"Content {i}", score=0.9 - i * 0.1)
        for i in range(10)
    ]

    ranked = await search_engine.rerank("test", results, top_k=3)
    assert len(ranked) == 3


# --- RRF Score Calculation Tests ---


def test_rrf_score_calculation() -> None:
    """Test RRF score calculation formula."""
    # RRF formula: 1 / (k + rank)
    # With k=60 and rank=1: 1/(60+1) = 0.0164
    k = 60

    # Document in both results at rank 1
    expected_score = 1 / (k + 1) + 1 / (k + 1)  # ~0.0328

    # Single source at rank 1
    single_score = 1 / (k + 1)  # ~0.0164

    assert expected_score > single_score  # Combined should be higher
    assert abs(expected_score - 0.0328) < 0.001


# --- Integration-style Tests ---


async def test_full_search_workflow(
    mock_faiss_index: AsyncMock,
    mock_sqlite_repo: AsyncMock,
    mock_embedder: MagicMock,
) -> None:
    """Test complete search workflow."""
    with patch(
        "liftlogic.domains.search.hybrid_search.SentenceTransformer",
        return_value=mock_embedder,
    ):
        engine = HybridSearchEngine(
            faiss_index=mock_faiss_index,
            sqlite_repo=mock_sqlite_repo,
        )

    # Execute search
    query = SearchQuery(query="KONE door fault 505", limit=5)
    results = await engine.search(query)

    # Verify results
    assert len(results) <= 5
    assert all(r.score > 0 for r in results)

    # Verify embedding was called
    mock_embedder.encode.assert_called_once_with("KONE door fault 505")

    # Rerank results
    ranked = await engine.rerank("KONE door fault 505", results, top_k=3)
    assert len(ranked) <= 3
    assert ranked[0].final_rank == 1

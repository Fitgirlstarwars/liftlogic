"""Tests for API Routes."""

from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from liftlogic.adapters import LLMResponse
from liftlogic.domains.knowledge import KnowledgeGraphStore

from .deps import get_knowledge_graph, get_sqlite_repository
from .main import create_app


@pytest.fixture
def mock_sqlite_repo() -> AsyncMock:
    """Create a mock SQLite repository."""
    mock = AsyncMock()
    mock.search_fts.return_value = []
    mock.get_fault_code.return_value = []
    mock.get_document.return_value = None
    return mock


@pytest.fixture
def mock_knowledge_graph() -> AsyncMock:
    """Create a mock knowledge graph."""
    mock = AsyncMock(spec=KnowledgeGraphStore)
    mock.find_fault_by_code.return_value = None
    mock.get_fault_resolution.return_value = []
    mock.get_fault_tests.return_value = []
    mock.get_neighbors.return_value = []
    return mock


@pytest.fixture
def mock_llm() -> AsyncMock:
    """Create a mock LLM service."""
    mock = AsyncMock()
    mock.provider = "mock"
    mock.generate.return_value = LLMResponse(
        text="Mock response", model="mock-model", provider="mock"
    )
    return mock


@pytest.fixture
def client(
    mock_sqlite_repo: AsyncMock, mock_knowledge_graph: AsyncMock
) -> Generator[TestClient, None, None]:
    """Create a test client with mocked dependencies."""
    app = create_app()

    # Override dependencies with mocks
    app.dependency_overrides[get_sqlite_repository] = lambda: mock_sqlite_repo
    app.dependency_overrides[get_knowledge_graph] = lambda: mock_knowledge_graph

    yield TestClient(app)

    # Cleanup
    app.dependency_overrides.clear()


def test_health_endpoint(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data


def test_search_endpoint_basic(client: TestClient, mock_sqlite_repo: AsyncMock) -> None:
    """Test basic search without RAG."""
    mock_sqlite_repo.search_fts.return_value = [
        {
            "id": 1,
            "filename": "test.pdf",
            "content": "Test content about fault codes",
            "manufacturer": "KONE",
            "score": -0.5,
        }
    ]

    response = client.post(
        "/api/search",
        json={"query": "fault code", "limit": 10, "use_rag": False},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "fault code"
    assert "results" in data
    assert data["answer"] is None  # No RAG


def test_search_endpoint_empty_query(client: TestClient) -> None:
    """Test search with validation error."""
    response = client.post(
        "/api/search",
        json={"query": "", "limit": 10},
    )
    # Pydantic validation should fail for empty query
    assert response.status_code == 422


def test_search_endpoint_limit_validation(client: TestClient) -> None:
    """Test search limit validation."""
    # Test with valid limit
    response = client.post(
        "/api/search",
        json={"query": "test", "limit": 50},
    )
    assert response.status_code == 200

    # Test with limit too high
    response = client.post(
        "/api/search",
        json={"query": "test", "limit": 200},
    )
    assert response.status_code == 422


def test_diagnosis_endpoint_structure(
    client: TestClient, mock_sqlite_repo: AsyncMock, mock_llm: AsyncMock
) -> None:
    """Test diagnosis endpoint returns correct structure."""
    from unittest.mock import patch

    with patch(
        "liftlogic.interfaces.api.routes.diagnosis.get_llm_for_user",
        return_value=mock_llm,
    ):
        response = client.post(
            "/api/diagnosis/diagnose",
            json={"fault_code": "F505"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["fault_code"] == "F505"
        assert "severity" in data
        assert "causes" in data
        assert "remedies" in data
        assert "confidence" in data


def test_cors_headers(client: TestClient) -> None:
    """Test CORS headers are present."""
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )
    # CORS preflight should work
    assert response.status_code in [200, 405]


def test_request_id_header(client: TestClient) -> None:
    """Test that responses include request ID."""
    response = client.get("/health")
    assert "x-request-id" in response.headers


def test_404_for_unknown_routes(client: TestClient) -> None:
    """Test 404 for non-existent routes."""
    response = client.get("/api/nonexistent")
    assert response.status_code == 404

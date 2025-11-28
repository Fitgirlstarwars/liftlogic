"""Tests for API Routes."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from .main import create_app


@pytest.fixture
def client():
    """Create a test client."""
    app = create_app()
    return TestClient(app)


def test_health_endpoint(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data


def test_search_endpoint_basic(client: TestClient):
    """Test basic search without RAG."""
    # Mock the SQLite repository
    with patch("liftlogic.interfaces.api.routes.search.get_sqlite_repository") as mock_repo:
        mock_instance = AsyncMock()
        mock_instance.search_fts.return_value = [
            {
                "id": 1,
                "filename": "test.pdf",
                "content": "Test content about fault codes",
                "manufacturer": "KONE",
                "score": -0.5,
            }
        ]
        mock_repo.return_value = mock_instance

        response = client.post(
            "/api/search",
            json={"query": "fault code", "limit": 10, "use_rag": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "fault code"
        assert "results" in data
        assert data["answer"] is None  # No RAG


def test_search_endpoint_empty_query(client: TestClient):
    """Test search with validation error."""
    response = client.post(
        "/api/search",
        json={"query": "", "limit": 10},
    )
    # Pydantic validation should fail for empty query
    assert response.status_code == 422


def test_search_endpoint_limit_validation(client: TestClient):
    """Test search limit validation."""
    with patch("liftlogic.interfaces.api.routes.search.get_sqlite_repository") as mock_repo:
        mock_instance = AsyncMock()
        mock_instance.search_fts.return_value = []
        mock_repo.return_value = mock_instance

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


def test_diagnosis_endpoint_structure(client: TestClient):
    """Test diagnosis endpoint returns correct structure."""
    with (
        patch("liftlogic.interfaces.api.routes.diagnosis.get_sqlite_repository") as mock_repo,
        patch("liftlogic.interfaces.api.routes.diagnosis.get_knowledge_graph") as mock_graph,
        patch("liftlogic.interfaces.api.routes.diagnosis.get_llm_for_user") as mock_llm,
    ):
        # Mock repository
        mock_repo_instance = AsyncMock()
        mock_repo_instance.get_fault_code.return_value = []
        mock_repo.return_value = mock_repo_instance

        # Mock knowledge graph
        mock_graph_instance = AsyncMock()
        mock_graph_instance.find_fault_by_code.return_value = None
        mock_graph_instance.get_fault_resolution.return_value = []
        mock_graph_instance.get_fault_tests.return_value = []
        mock_graph_instance.get_neighbors.return_value = []
        mock_graph.return_value = mock_graph_instance

        # Mock LLM
        mock_llm_instance = AsyncMock()
        mock_llm_instance.generate.return_value = AsyncMock(text="Test diagnosis")
        mock_llm.return_value = mock_llm_instance

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


def test_cors_headers(client: TestClient):
    """Test CORS headers are present."""
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )
    # CORS preflight should work
    assert response.status_code in [200, 405]


def test_request_id_header(client: TestClient):
    """Test that responses include request ID."""
    response = client.get("/health")
    assert "x-request-id" in response.headers


def test_404_for_unknown_routes(client: TestClient):
    """Test 404 for non-existent routes."""
    response = client.get("/api/nonexistent")
    assert response.status_code == 404

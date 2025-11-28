# Testing Guide

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=liftlogic --cov-report=html

# Run specific domain
pytest liftlogic/domains/search/

# Run single file
pytest liftlogic/domains/search/test_hybrid_search.py

# Verbose output
pytest -v --tb=short
```

## Test File Location

Tests are **co-located** with source code:

```
liftlogic/domains/search/
├── hybrid_search.py
├── test_hybrid_search.py    # Tests for hybrid_search
├── models.py
└── test_models.py           # Tests for models
```

## Async Test Pattern

All tests use `pytest-asyncio` with auto mode:

```python
import pytest
from liftlogic.domains.search import HybridSearchEngine, SearchQuery

# No decorator needed - asyncio_mode = "auto" in pyproject.toml
async def test_search_returns_results():
    engine = HybridSearchEngine(...)
    query = SearchQuery(query="test query")

    results = await engine.search(query)

    assert len(results) >= 0
```

## Mocking Adapters

### Mock GeminiClient

```python
from unittest.mock import AsyncMock
from liftlogic.adapters.gemini import GeminiClient, GeminiResponse

@pytest.fixture
def mock_gemini():
    client = AsyncMock(spec=GeminiClient)
    client.generate.return_value = GeminiResponse(
        text="Mocked response",
        model="gemini-2.0-flash",
        tokens_used=100,
    )
    client.generate_json.return_value = {
        "components": [],
        "connections": [],
    }
    return client
```

### Mock SQLiteRepository

```python
from unittest.mock import AsyncMock
from liftlogic.adapters.sqlite import SQLiteRepository

@pytest.fixture
def mock_sqlite():
    repo = AsyncMock(spec=SQLiteRepository)
    repo.search_fts.return_value = [
        {"id": 1, "content": "test", "score": 0.9}
    ]
    return repo
```

### Mock FAISSIndex

```python
import numpy as np
from unittest.mock import AsyncMock
from liftlogic.adapters.faiss import FAISSIndex

@pytest.fixture
def mock_faiss():
    index = AsyncMock(spec=FAISSIndex)
    index.search.return_value = [
        (0.95, 1, {"doc_id": 1}),
        (0.85, 2, {"doc_id": 2}),
    ]
    return index
```

## Testing Domains

### Test Extraction

```python
from pathlib import Path
from liftlogic.domains.extraction import GeminiExtractor, PDFDocument

async def test_extraction(mock_gemini, tmp_path):
    # Create test PDF (or use fixture)
    pdf_path = tmp_path / "test.pdf"
    # ... create minimal PDF ...

    extractor = GeminiExtractor(mock_gemini)
    doc = PDFDocument(path=pdf_path)

    result = await extractor.extract(doc)

    assert result.source_file == "test.pdf"
    mock_gemini.extract_pdf.assert_called_once()
```

### Test Search

```python
from liftlogic.domains.search import HybridSearchEngine, SearchQuery

async def test_hybrid_search(mock_sqlite, mock_faiss):
    engine = HybridSearchEngine(
        sqlite_repo=mock_sqlite,
        faiss_index=mock_faiss,
    )

    results = await engine.search(SearchQuery(query="test"))

    assert isinstance(results, list)
```

### Test Diagnosis

```python
from liftlogic.domains.diagnosis import FaultDiagnosisAgent, DiagnosisMode

async def test_diagnosis(mock_gemini):
    agent = FaultDiagnosisAgent(llm_client=mock_gemini)

    diagnosis = await agent.diagnose(
        fault_code="F505",
        mode=DiagnosisMode.QUICK,
    )

    assert diagnosis.fault_code == "F505"
    assert diagnosis.severity is not None
```

## Testing API Routes

```python
from fastapi.testclient import TestClient
from liftlogic.interfaces.api import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_search_endpoint(client):
    response = client.post("/api/search", json={
        "query": "test query",
        "limit": 10,
    })
    assert response.status_code == 200
```

## Testing CLI Commands

```python
from typer.testing import CliRunner
from liftlogic.interfaces.cli import app

runner = CliRunner()

def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "2.0.0" in result.stdout

def test_diagnose_command():
    result = runner.invoke(app, ["diagnose", "F505"])
    assert result.exit_code == 0
```

## Fixtures for Common Objects

Create `conftest.py` in test directories:

```python
# liftlogic/conftest.py
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_settings():
    from liftlogic.config import Settings
    return Settings(
        google_api_key="test-key",
        data_dir="/tmp/test-data",
    )

@pytest.fixture
def sample_extraction_result():
    from liftlogic.domains.extraction import ExtractionResult
    return ExtractionResult(
        source_file="test.pdf",
        components=[],
        connections=[],
        fault_codes=[],
    )
```

## Integration Tests

For integration tests that need real services:

```python
import pytest

@pytest.mark.integration
async def test_real_gemini_extraction():
    """Requires GOOGLE_API_KEY environment variable."""
    from liftlogic.adapters.gemini import GeminiClient
    from liftlogic.config import get_settings

    settings = get_settings()
    if not settings.google_api_key:
        pytest.skip("No API key configured")

    client = GeminiClient(api_key=settings.google_api_key)
    response = await client.generate("Hello")
    assert response.text
```

Run integration tests:
```bash
pytest -m integration
```

## Coverage Requirements

Aim for:
- **80%+** coverage on domain logic
- **70%+** coverage on adapters
- **60%+** coverage on interfaces

Check coverage:
```bash
pytest --cov=liftlogic --cov-report=term-missing
```

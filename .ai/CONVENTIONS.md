# LiftLogic Coding Conventions

## File Structure

```python
# Every file follows this pattern:
"""
{Module Name} - {One line description}

{Detailed description if needed}
"""

from __future__ import annotations

# Standard library
import asyncio
from typing import TYPE_CHECKING

# Third party
from pydantic import BaseModel

# Local - relative imports within domain
from .contracts import SomeProtocol
from .models import SomeModel

# Type checking only imports
if TYPE_CHECKING:
    from adapters.gemini import GeminiClient

__all__ = ["PublicClass", "public_function"]


class PublicClass:
    """Docstring with example."""
    pass
```

## Naming

| Type | Convention | Example |
|------|------------|---------|
| Files | snake_case | `hybrid_search.py` |
| Classes | PascalCase | `HybridSearchEngine` |
| Functions | snake_case | `search_documents()` |
| Constants | UPPER_SNAKE | `MAX_RESULTS = 100` |
| Private | _prefix | `_internal_helper()` |

## Type Hints

```python
# Always use type hints
async def search(query: str, limit: int = 10) -> list[SearchResult]:
    ...

# Use Protocol for interfaces
class Searcher(Protocol):
    async def search(self, query: str) -> list[Result]: ...
```

## Async

```python
# Prefer async for I/O operations
async def fetch_document(doc_id: str) -> Document:
    ...

# Use asyncio.gather for parallel operations
results = await asyncio.gather(
    fetch_document("a"),
    fetch_document("b"),
)
```

## Error Handling

```python
# Define domain-specific exceptions
class ExtractionError(Exception):
    """Base exception for extraction domain."""
    pass

class PDFParseError(ExtractionError):
    """Failed to parse PDF."""
    pass

# Raise with context
raise PDFParseError(f"Failed to parse {pdf_path}: {reason}")
```

## Testing

```python
# Tests live next to source
# domains/search/tests/test_hybrid.py

import pytest
from ..hybrid_search import HybridSearchEngine

@pytest.fixture
def engine():
    return HybridSearchEngine()

async def test_search_returns_results(engine):
    results = await engine.search("fault 505")
    assert len(results) > 0
```

## Imports Between Layers

```python
# ALLOWED
from domains.search import SearchEngine          # interface imports domain
from adapters.gemini import GeminiClient         # domain imports adapter
from liftlogic.config import settings            # anyone imports config

# FORBIDDEN
from interfaces.api import app                   # domain importing interface
from domains.search import SearchEngine          # adapter importing domain
```

## Pydantic Models

```python
from pydantic import BaseModel, Field

class SearchQuery(BaseModel):
    """Search request model."""

    query: str = Field(..., min_length=1, description="Search query text")
    limit: int = Field(default=10, ge=1, le=100)
    filters: dict[str, str] = Field(default_factory=dict)

    model_config = {"frozen": True}  # Immutable
```

## Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate levels
logger.debug("Processing document %s", doc_id)
logger.info("Extracted %d components", count)
logger.warning("Rate limit approaching: %d/60", current)
logger.error("Failed to connect: %s", error)
```

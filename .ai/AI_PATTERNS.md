# CLAUDE.md - AI Coding Instructions

> **READ THIS FIRST** when working on this codebase.

## Project Summary

LiftLogic is an AI-native elevator/lift technical documentation system. It extracts data from PDFs, enables hybrid search, and provides expert fault diagnosis.

## Critical Rules

### 1. Layer Import Restrictions (NEVER VIOLATE)
```
interfaces/ → can import from → domains/, adapters/, config/
domains/    → can import from → adapters/, config/
adapters/   → can import from → config/ ONLY
config/     → imports nothing from liftlogic
```

**Use `TYPE_CHECKING` for type hints that would create circular imports:**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from liftlogic.adapters.gemini import GeminiClient
```

### 2. Every Domain Has This Structure
```
domains/{name}/
├── __init__.py      # Exports public API
├── contracts.py     # Protocol interfaces (ALWAYS CHECK FIRST)
├── models.py        # Pydantic data types
└── {impl}.py        # Implementation files
```

**When adding features:** Check `contracts.py` first to understand the interface.

### 3. Async Patterns
- ALL adapter methods are `async`
- ALL domain methods are `async`
- Use `asyncio.to_thread()` for blocking I/O
- Never use `time.sleep()` - use `asyncio.sleep()`

### 4. Pydantic Models
- Use `Field(default_factory=list)` for mutable defaults
- Frozen models use `@model_validator(mode="before")` for computed fields
- Always use type hints: `list[str]` not `List[str]`

## Common Gotchas

### Gemini API Rate Limiting
The `GeminiClient` has built-in rate limiting (15 RPM default). When making multiple calls:
```python
# The client handles this automatically via semaphore
# But for batch operations, use built-in batch methods
results = await gemini.extract_pdf(pdf_path)  # Uses File API correctly
```

### Neo4j Transactions
Always use async context manager:
```python
async with neo4j_client.session() as session:
    await session.run(query, params)
```

### FAISS Index Persistence
FAISS operations are CPU-bound. Already wrapped in `asyncio.to_thread()`.
```python
await faiss_index.save(path)  # Non-blocking
await faiss_index.load(path)  # Non-blocking
```

### SearchQuery vs Query (Orchestration)
- `domains/search/models.py` has `SearchQuery` with field `query: str`
- `domains/orchestration/models.py` has `Query` with field `text: str`
- Don't confuse them! Check imports.

## File Size Limit

**Max 500 lines per file.** If approaching limit, split into:
- `{module}_core.py` - Main logic
- `{module}_utils.py` - Helper functions
- `{module}_types.py` - Additional types

## Testing Patterns

Tests live next to source code:
```
domains/search/
├── hybrid_search.py
└── test_hybrid_search.py  # Co-located
```

Mock adapters, not domains:
```python
@pytest.fixture
def mock_gemini():
    client = AsyncMock(spec=GeminiClient)
    client.generate.return_value = GeminiResponse(text="test")
    return client
```

## Error Handling

Each domain can define exceptions in a `exceptions.py` file:
```python
class ExtractionError(Exception):
    """Base extraction error."""
    pass

class PDFParseError(ExtractionError):
    """Failed to parse PDF."""
    pass
```

API routes should catch domain exceptions and return appropriate HTTP codes.

## Adding a New Feature Checklist

1. [ ] Define types in `models.py`
2. [ ] Add protocol method to `contracts.py`
3. [ ] Implement in appropriate file
4. [ ] Export in `__init__.py`
5. [ ] Add API route if user-facing
6. [ ] Add CLI command if applicable
7. [ ] Write tests

## Quick Reference

| Need to... | Look in... |
|------------|------------|
| Add Gemini call | `adapters/gemini/client.py` |
| Add search feature | `domains/search/` |
| Add diagnosis logic | `domains/diagnosis/expert_agents.py` |
| Add API endpoint | `interfaces/api/routes/` |
| Add CLI command | `interfaces/cli/main.py` |
| Change settings | `config/settings.py` |

## Do NOT

- Import domains from adapters
- Use blocking I/O in async functions without `to_thread()`
- Create new Gemini client instances (use dependency injection)
- Skip type hints
- Write files > 500 lines
- Add features without updating `__init__.py` exports

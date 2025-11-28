# LiftLogic - AI-Native Elevator Intelligence System

## Quick Context
- **What**: PDF extraction → hybrid search → fault diagnosis for elevator technicians
- **Stack**: Python 3.11+, FastAPI, Gemini 2.0 (OAuth/ADC), FAISS, Neo4j, React/TypeScript
- **Entry point**: `liftlogic serve` or `uvicorn liftlogic.interfaces.api.main:app`
- **LLM Cost**: Zero (uses OAuth/ADC, no API keys)

## Zero API Cost Setup
```bash
# One-time: authenticate with Google Cloud
gcloud auth application-default login

# That's it! No API keys needed.
```

## Model Selection (Claude Code)
Default model: **Opus 4.5** (configured in `.claude/settings.json`)

| Task Type | Model | Command |
|-----------|-------|---------|
| Complex refactoring, multi-file changes | `opus` | `/model opus` |
| Routine coding, quick fixes | `sonnet` | `/model sonnet` |
| Simple tasks, quick questions | `haiku` | `/model haiku` |

## Project Structure
```
liftlogic/
├── adapters/       # External services (Gemini, SQLite, FAISS, Neo4j)
├── domains/        # Business logic (extraction, search, knowledge, diagnosis, orchestration)
├── interfaces/     # User-facing (api/, cli/, web/)
├── config/         # Settings, errors, manifests
└── tools/          # Migration/import scripts
data/
├── processed/platinum/  # 2,307 pre-extracted documents
└── graph/              # 1,043 nodes, 432 edges
```

## Layer Import Rules (NEVER VIOLATE)
- `interfaces/` → can import → `domains/`, `adapters/`, `config/`
- `domains/` → can import → `adapters/`, `config/`
- `adapters/` → can import → `config/` ONLY
- Use `TYPE_CHECKING` for circular import prevention

## Domain Pattern
Every domain has:
- `contracts.py` - Protocol interfaces (check FIRST)
- `models.py` - Pydantic data types
- `__init__.py` - Public exports

## Code Conventions
- Type hints mandatory: `list[str]` not `List[str]`
- Async everywhere: all adapter/domain methods are `async`
- Use `asyncio.to_thread()` for blocking I/O
- Use `Field(default_factory=list)` for mutable defaults
- Max 500 lines per file
- Use `ErrorCode` from `config.errors` for exceptions
- Use `ArtifactManifest` for tracking indices/exports

## Common Commands
```bash
liftlogic serve              # Start API (port 8000)
liftlogic diagnose F505      # Diagnose fault code
liftlogic extract manual.pdf # Extract PDF
pytest                       # Run tests
mypy liftlogic              # Type check
ruff check .                # Lint
python3 tools/import_data.py # Import pre-processed data
```

## Custom Slash Commands
```
/project:test [domain]       # Run tests
/project:serve [--reload]    # Start dev server
/project:check               # Run mypy + ruff + pytest
/project:diagnose <code>     # Test fault diagnosis
/project:extract <pdf>       # Extract PDF data
/project:add-feature <domain> <name>  # Guided feature workflow
```

## Key Files
| Need | File |
|------|------|
| Add Gemini call | `adapters/gemini/client.py` |
| Add search feature | `domains/search/hybrid_search.py` |
| Add diagnosis logic | `domains/diagnosis/expert_agents.py` |
| Add API endpoint | `interfaces/api/routes/` |
| Add CLI command | `interfaces/cli/main.py` |
| Change settings | `config/settings.py` |
| Add error codes | `config/errors.py` |
| Track artifacts | `config/manifest.py` |
| API middleware | `interfaces/api/middleware.py` |

## API Features
- Request ID tracking (`X-Request-ID` header)
- Latency measurement (`X-Response-Time-Ms` header)
- Rate limiting (60 req/min per IP, `X-RateLimit-*` headers)
- Structured errors with `ErrorCode` taxonomy

## Do NOT
- Import domains from adapters
- Use blocking I/O without `to_thread()`
- Create new Gemini instances (use dependency injection)
- Skip type hints
- Write files > 500 lines
- Add features without updating `__init__.py` exports
- Use API keys (OAuth/ADC only)
- Write to `.env` files (denied by permissions)

## Pre-loaded Data
- **2,307 platinum JSONs**: High-quality extractions (OTIS, KONE, etc.)
- **1,043 graph nodes**: Fault codes, components, procedures
- **432 graph edges**: Relationships and causation chains
- Run `python3 tools/import_data.py` to refresh

## Extended Documentation
@.ai/CONTEXT.md
@.ai/CONVENTIONS.md
@.ai/API_GUIDE.md
@.ai/TESTING.md
@.ai/WORKFLOWS.md
@.ai/SETUP.md

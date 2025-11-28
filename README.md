# LiftLogic

AI-native elevator/lift technical documentation intelligence system.

## Quick Start

```bash
# Install
pip install -e .

# Set up environment
cp .env.example .env  # Edit with your GOOGLE_API_KEY

# Initialize database
python tools/migrations/init_database.py

# Run API server
liftlogic serve

# Or use CLI directly
liftlogic diagnose F505
liftlogic extract manual.pdf
liftlogic search "KONE door fault"
```

## For AI Agents / LLM Coders

**Start here:** `.ai/CLAUDE.md` - AI-specific patterns and gotchas

**Documentation:**
| File | Purpose |
|------|---------|
| `.ai/CONTEXT.md` | Architecture overview (read first) |
| `.ai/CONVENTIONS.md` | Coding standards |
| `.ai/CLAUDE.md` | AI coding instructions |
| `.ai/API_GUIDE.md` | API endpoint reference |
| `.ai/TESTING.md` | Testing patterns |
| `.ai/WORKFLOWS.md` | Data flow diagrams |
| `.ai/SETUP.md` | Installation guide |

## Architecture

```
liftlogic/
├── adapters/           # External services (Gemini, SQLite, FAISS, Neo4j)
├── domains/            # Business logic
│   ├── extraction/     # PDF → structured data
│   ├── search/         # Hybrid RAG search
│   ├── knowledge/      # Graph store + reasoning
│   ├── diagnosis/      # Expert agents
│   └── orchestration/  # Query routing + caching
├── interfaces/
│   ├── api/            # FastAPI REST API
│   ├── cli/            # Typer CLI
│   └── web/            # React frontend
├── config/             # Pydantic settings
└── tools/              # Migration scripts
```

**Import Rules:**
- `interfaces/` → can import from → `domains/`, `adapters/`
- `domains/` → can import from → `adapters/`
- `adapters/` → imports nothing from liftlogic

## Key Features

| Feature | Description |
|---------|-------------|
| **PDF Extraction** | Extract components, connections, fault codes from technical manuals |
| **Hybrid Search** | FAISS vectors + SQLite FTS5 + RRF fusion |
| **Knowledge Graph** | NetworkX (in-memory) + Neo4j (persistent) |
| **Expert Diagnosis** | Multi-agent fault analysis with consensus |
| **Smart Routing** | Pattern + LLM query classification |
| **Response Caching** | TTL-based with LRU eviction |

## Tech Stack

- **LLM**: Google Gemini 2.0 Flash
- **Vector DB**: FAISS
- **Graph DB**: Neo4j (optional)
- **SQL**: SQLite with FTS5
- **API**: FastAPI
- **CLI**: Typer + Rich
- **Frontend**: React + TypeScript + TailwindCSS

## API Endpoints

```http
GET  /health                    # Health check
POST /api/search                # Hybrid search (with optional RAG)
POST /api/extraction/extract    # Extract PDF
POST /api/diagnosis/diagnose    # Fault diagnosis
```

See `.ai/API_GUIDE.md` for full documentation.

## CLI Commands

```bash
liftlogic serve                 # Start API server
liftlogic search "query"        # Search knowledge base
liftlogic diagnose F505         # Diagnose fault code
liftlogic extract manual.pdf    # Extract PDF
liftlogic init                  # Initialize database
liftlogic version               # Show version
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy liftlogic

# Linting
ruff check .
```

## Configuration

Create `.env` file:

```env
GOOGLE_API_KEY=your-gemini-api-key
DATA_DIR=data
GEMINI_MODEL=gemini-2.0-flash
```

See `.ai/SETUP.md` for full configuration options.

## License

MIT

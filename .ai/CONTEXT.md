# LiftLogic AI Context

**Read this first. 50 lines. Everything you need to start.**

## What Is This?

LiftLogic is an AI system for elevator/lift technical documentation:
- Ingests PDF manuals → extracts structured data (fault codes, components, procedures)
- Provides intelligent search (vector + keyword + graph hybrid)
- Offers expert diagnosis (safety audits, maintenance schedules)

## Architecture (5 minutes to understand)

```
liftlogic/
├── domains/        # Business logic (START HERE for features)
│   ├── extraction/ # PDF → Structured JSON
│   ├── search/     # Query → Results
│   ├── knowledge/  # Graph reasoning
│   ├── diagnosis/  # Fault analysis
│   └── orchestration/ # Model routing, caching
│
├── adapters/       # External services (wrapped)
│   ├── gemini/     # ALL Gemini API calls go here
│   ├── sqlite/     # Document storage
│   ├── faiss/      # Vector search
│   └── neo4j/      # Graph database
│
├── interfaces/     # User-facing
│   ├── api/        # FastAPI REST endpoints
│   ├── cli/        # Command-line tools
│   └── web/        # React frontend
│
└── config/         # Settings
```

## Key Rules

1. **domains/** never imports from **interfaces/**
2. **adapters/** never imports from **domains/**
3. ALL Gemini calls go through `adapters/gemini/client.py`
4. Tests are co-located: `domains/search/tests/test_hybrid.py`
5. Every module has `contracts.py` (interfaces) and `models.py` (types)
6. Max 500 lines per file

## Common Tasks

### Add extraction feature
1. Update `domains/extraction/contracts.py`
2. Update `domains/extraction/models.py`
3. Implement in `domains/extraction/{feature}.py`
4. Add tests in `domains/extraction/tests/`

### Add API endpoint
1. Create route in `interfaces/api/routes/{name}.py`
2. Register in `interfaces/api/main.py`

### Add external service
1. Create adapter in `adapters/{service}/`
2. Add to dependency injection in `interfaces/api/deps.py`

## Data Location

- Raw PDFs: `data/raw/manuals/` (symlink to external drive)
- Processed: `data/processed/`
- Vector index: `data/indices/faiss/`
- SQLite DB: `data/liftlogic.db`

# Setup Guide

## Quick Start

```bash
cd /Users/fender/Desktop/liftlogic

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package
pip install -e ".[dev]"

# Initialize database
python tools/migrations/init_database.py --db data/liftlogic.db

# Run API server
liftlogic serve
```

---

## Environment Configuration

Create `.env` file in project root:

```env
# Required
GOOGLE_API_KEY=your-gemini-api-key

# Optional - Defaults shown
DATA_DIR=data
DB_PATH=data/liftlogic.db
FAISS_INDEX_PATH=data/faiss_index

# Gemini Settings
GEMINI_MODEL=gemini-2.0-flash
GEMINI_TEMPERATURE=0.1
GEMINI_RATE_LIMIT_RPM=15

# Neo4j (optional)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# Ollama (optional, for local LLM)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Search Settings
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
SEARCH_DEFAULT_LIMIT=20

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# Monitoring (optional)
PHOENIX_ENABLED=false
PHOENIX_ENDPOINT=http://localhost:6006
```

---

## Database Setup

### SQLite (Default)

Automatically created on first run. To initialize manually:

```bash
python tools/migrations/init_database.py --db data/liftlogic.db
```

### Neo4j (Optional)

For knowledge graph persistence:

```bash
# Using Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# Verify connection
curl http://localhost:7474
```

---

## FAISS Index

The FAISS index is created automatically when first document is indexed.

To manually create:

```python
from liftlogic.adapters.faiss import FAISSIndex

index = FAISSIndex(dimension=384)
await index.save("data/faiss_index")
```

---

## Migrate from Old EVIH

If migrating from the old EVIH project:

```bash
python tools/migrations/migrate_from_evih.py \
  --source /path/to/old/evih \
  --dest data/

# Or create symlink to existing data
python tools/migrations/migrate_from_evih.py \
  --source /path/to/old/evih \
  --dest data/ \
  --symlink
```

---

## Web Frontend Setup

```bash
cd liftlogic/interfaces/web

# Install dependencies
npm install

# Development server
npm run dev

# Production build
npm run build
```

---

## Verify Installation

```bash
# Check CLI
liftlogic version

# Check API
liftlogic serve &
curl http://localhost:8000/health

# Run tests
pytest
```

---

## Common Issues

### "No module named 'liftlogic'"

```bash
pip install -e .
```

### "GOOGLE_API_KEY not set"

Create `.env` file or set environment variable:
```bash
export GOOGLE_API_KEY=your-key
```

### "Neo4j connection refused"

Neo4j is optional. To disable:
- Don't set NEO4J_URI in .env
- The system will use NetworkX in-memory graph only

### FAISS import error

```bash
pip install faiss-cpu
# Or for GPU:
pip install faiss-gpu
```

### "Rate limit exceeded" (Gemini)

The default rate limit is 15 RPM. Adjust in .env:
```
GEMINI_RATE_LIMIT_RPM=30
```

---

## Development Setup

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run linting
ruff check .

# Run type checking
mypy liftlogic

# Run tests with coverage
pytest --cov=liftlogic

# Format code
ruff format .
```

---

## Docker Setup (Optional)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e .

EXPOSE 8000
CMD ["liftlogic", "serve", "--host", "0.0.0.0"]
```

```bash
docker build -t liftlogic .
docker run -p 8000:8000 -e GOOGLE_API_KEY=your-key liftlogic
```

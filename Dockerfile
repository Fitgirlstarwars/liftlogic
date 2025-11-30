# Build stage for React frontend
# Cache buster: 2025-11-29T12:00:00Z - Updated default model to gemini-2.5-flash
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend
COPY liftlogic/interfaces/web/package*.json ./
RUN npm ci
COPY liftlogic/interfaces/web/ ./
RUN npm run build

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies and install
COPY pyproject.toml README.md ./
COPY liftlogic/ ./liftlogic/
COPY tools/ ./tools/

# Install the package
RUN pip install --no-cache-dir .

# Copy landing page
COPY liftlogic/interfaces/landing/ ./liftlogic/interfaces/landing/

# Copy built React app from frontend builder
COPY --from=frontend-builder /app/frontend/dist ./liftlogic/interfaces/web/dist

# Copy pre-built data (37MB total - includes 2,307 docs indexed in SQLite)
# Database is pre-built with FTS5 full-text search
COPY data/liftlogic.db ./data/liftlogic.db
COPY data/graph/ ./data/graph/
COPY data/index.json ./data/index.json

# Expose port (Cloud Run uses PORT env var, default 8080)
EXPOSE 8080

# Run the application
# Cloud Run sets PORT env var; fallback to 8080
CMD ["sh", "-c", "uvicorn liftlogic.interfaces.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

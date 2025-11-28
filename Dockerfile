# Build stage for React frontend
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

# Create data directory
RUN mkdir -p data

# Expose port
EXPOSE 10000

# Run the application
CMD ["uvicorn", "liftlogic.interfaces.api.main:app", "--host", "0.0.0.0", "--port", "10000"]

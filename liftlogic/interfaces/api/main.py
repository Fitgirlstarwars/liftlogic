"""
FastAPI Main Application - Unified API entry point.

Run with: uvicorn liftlogic.interfaces.api.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from liftlogic.config import get_settings

from .deps import cleanup_services, init_services
from .middleware import (
    ErrorHandlerMiddleware,
    LatencyMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
)
from .routes import diagnosis, extraction, health, search

# Static file paths
INTERFACES_DIR = Path(__file__).parent.parent
LANDING_DIR = INTERFACES_DIR / "landing"
WEB_DIST_DIR = INTERFACES_DIR / "web" / "dist"

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    logger.info("Starting LiftLogic API...")
    logger.info("  Data dir: %s", settings.data_dir)
    logger.info("  LLM mode: OAuth/ADC (zero API cost)")

    # Initialize resources (SQLite, knowledge graph)
    await init_services()
    logger.info("  Services initialized")

    yield

    # Cleanup
    logger.info("Shutting down LiftLogic API...")
    await cleanup_services()


def create_app() -> FastAPI:
    """Create FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="LiftLogic API",
        description="AI-native elevator/lift technical documentation intelligence",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add middleware (order matters - first added = outermost)
    # 1. Rate limiting (outermost - reject early)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

    # 2. Error handling (catch exceptions from inner layers)
    app.add_middleware(ErrorHandlerMiddleware)

    # 3. Latency tracking
    app.add_middleware(LatencyMiddleware)

    # 4. Request ID (innermost custom - runs first)
    app.add_middleware(RequestIDMiddleware)

    # 5. CORS (framework middleware)
    # Security: Explicitly list allowed origins instead of "*"
    allowed_origins = [
        "http://localhost:3000",  # Vite dev server
        "http://localhost:8000",  # FastAPI (same-origin)
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    # Add production origins from environment if configured
    if settings.api_debug:
        # In debug mode, also allow any localhost port for development
        allowed_origins.append("http://localhost:*")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    )

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(search.router, prefix="/api/search", tags=["Search"])
    app.include_router(extraction.router, prefix="/api/extraction", tags=["Extraction"])
    app.include_router(diagnosis.router, prefix="/api/diagnosis", tags=["Diagnosis"])

    # Serve the React app (Technician Portal) at /app
    if WEB_DIST_DIR.exists():
        # Serve React app static assets
        app.mount(
            "/app/assets",
            StaticFiles(directory=WEB_DIST_DIR / "assets"),
            name="app-assets",
        )

        @app.get("/app")
        @app.get("/app/{path:path}")
        async def serve_react_app(request: Request, path: str = ""):
            """Serve the React technician portal (LiftLogic app)."""
            return FileResponse(WEB_DIST_DIR / "index.html")

    # Serve the landing page (ARPRO website) at root
    if LANDING_DIR.exists():
        # Mount landing page assets
        app.mount(
            "/assets",
            StaticFiles(directory=LANDING_DIR / "assets"),
            name="landing-assets",
        )

        @app.get("/styles.css")
        async def serve_landing_css():
            """Serve landing page CSS."""
            return FileResponse(LANDING_DIR / "styles.css", media_type="text/css")

        @app.get("/script.js")
        async def serve_landing_js():
            """Serve landing page JavaScript."""
            return FileResponse(LANDING_DIR / "script.js", media_type="application/javascript")

        @app.get("/")
        async def serve_landing_page():
            """Serve the main ARPRO landing page."""
            return FileResponse(LANDING_DIR / "index.html")

    return app


# Create app instance
app = create_app()

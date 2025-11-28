"""
API Dependencies - Dependency injection for FastAPI routes.

Provides singleton instances of database and service objects.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from liftlogic.adapters.sqlite import SQLiteRepository
from liftlogic.config import get_settings
from liftlogic.domains.knowledge import KnowledgeGraphStore


@lru_cache
def get_sqlite_repository() -> SQLiteRepository:
    """Get SQLite repository singleton."""
    settings = get_settings()
    return SQLiteRepository(settings.db_path)


@lru_cache
def get_knowledge_graph() -> KnowledgeGraphStore:
    """Get knowledge graph store singleton."""
    return KnowledgeGraphStore()


async def init_services() -> None:
    """
    Initialize services on startup.

    This should be called from the FastAPI lifespan handler.
    """
    settings = get_settings()

    # Initialize SQLite
    repo = get_sqlite_repository()
    await repo.initialize()

    # Load knowledge graph from JSON
    graph = get_knowledge_graph()
    graph_dir = Path(settings.data_dir) / "graph"
    if graph_dir.exists():
        await graph.load_from_json(graph_dir)


async def cleanup_services() -> None:
    """Cleanup services on shutdown."""
    repo = get_sqlite_repository()
    await repo.close()

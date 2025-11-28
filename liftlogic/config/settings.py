"""
Settings - Application configuration using Pydantic Settings.

Loads from environment variables and .env files.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # LLM Provider: "oauth" (ADC, zero cost) or "ollama" (local)
    # No API keys - use `gcloud auth application-default login` for OAuth
    llm_provider: str = "oauth"

    # Paths
    data_dir: Path = Path("data")
    db_path: Path = Path("data/liftlogic.db")
    faiss_index_path: Path = Path("data/indices/faiss")

    # Gemini (via OAuth/ADC - no API key needed)
    gemini_model: str = "gemini-2.0-flash"
    gemini_temperature: float = 1.0
    gemini_rate_limit_rpm: int = 60

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"

    # Ollama
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Search
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    search_default_limit: int = 20

    # Monitoring
    phoenix_enabled: bool = False
    phoenix_endpoint: str = "http://localhost:6006/v1/traces"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

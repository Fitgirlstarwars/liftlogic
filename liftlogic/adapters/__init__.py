"""
Adapters - External service integrations.

All external API calls are wrapped here to isolate domains from third-party changes.
"""

from .faiss import FAISSIndex
from .gemini import GeminiClient
from .llm import LLMResponse, LLMService, get_llm_for_user
from .neo4j import Neo4jClient
from .sqlite import SQLiteRepository

__all__ = [
    # Original adapters
    "GeminiClient",
    "SQLiteRepository",
    "FAISSIndex",
    "Neo4jClient",
    # Unified LLM (per-user OAuth + Ollama fallback)
    "LLMService",
    "get_llm_for_user",
    "LLMResponse",
]

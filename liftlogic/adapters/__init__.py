"""
Adapters - External service integrations.

All external API calls are wrapped here to isolate domains from third-party changes.
"""

from .gemini import GeminiClient
from .sqlite import SQLiteRepository
from .faiss import FAISSIndex
from .neo4j import Neo4jClient
from .llm import LLMService, get_llm_for_user, LLMResponse

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

"""
LLM Adapter - Unified interface for language model access.

Supports:
- Gemini with user OAuth tokens (zero cost, user's quota)
- Ollama for local/fallback (your server, no auth needed)

Usage:
    from liftlogic.adapters.llm import LLMService, get_llm_for_user

    # With authenticated user
    llm = await get_llm_for_user(user_context)
    response = await llm.generate("What is fault code 505?")

    # Without auth (uses Ollama)
    llm = await get_llm_for_user(None)
    response = await llm.generate("What is fault code 505?")
"""

from .service import LLMService, get_llm_for_user, LLMResponse

__all__ = ["LLMService", "get_llm_for_user", "LLMResponse"]

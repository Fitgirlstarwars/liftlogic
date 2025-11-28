"""
Gemini Adapter - Unified Google Gemini API client.

This is the ONLY place that calls the Gemini API.
All domains use this adapter for LLM operations.
"""

from .client import GeminiClient
from .models import (
    GeminiConfig,
    GeminiRequest,
    GeminiResponse,
    ExtractionRequest,
    ExtractionResponse,
)

__all__ = [
    "GeminiClient",
    "GeminiConfig",
    "GeminiRequest",
    "GeminiResponse",
    "ExtractionRequest",
    "ExtractionResponse",
]

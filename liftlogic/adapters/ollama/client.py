"""
Ollama Client - Local LLM for RAG responses.

Features:
- Async HTTP client
- Streaming support
- Multiple model support
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

logger = logging.getLogger(__name__)

__all__ = ["OllamaClient"]


class OllamaClient:
    """
    Ollama local LLM client.

    Example:
        >>> client = OllamaClient()
        >>> response = await client.generate("llama3.2", "What is fault 505?")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
    ) -> None:
        """
        Initialize Ollama client.

        Args:
            base_url: Ollama server URL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def generate(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate text response.

        Args:
            model: Model name (e.g., "llama3.2")
            prompt: User prompt
            system: Optional system prompt
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        client = await self._get_client()

        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system

        response = await client.post("/api/generate", json=payload)
        response.raise_for_status()

        data = response.json()
        return data.get("response", "")

    async def stream_generate(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream generated text.

        Args:
            model: Model name
            prompt: User prompt
            system: Optional system prompt

        Yields:
            Text chunks
        """
        client = await self._get_client()

        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": True,
        }
        if system:
            payload["system"] = system

        async with client.stream("POST", "/api/generate", json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        """
        Chat completion.

        Args:
            model: Model name
            messages: List of {"role": "user/assistant", "content": "..."}
            temperature: Sampling temperature

        Returns:
            Assistant response
        """
        client = await self._get_client()

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        response = await client.post("/api/chat", json=payload)
        response.raise_for_status()

        data = response.json()
        return data.get("message", {}).get("content", "")

    async def list_models(self) -> list[str]:
        """List available models."""
        client = await self._get_client()
        response = await client.get("/api/tags")
        response.raise_for_status()

        data = response.json()
        return [m["name"] for m in data.get("models", [])]

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

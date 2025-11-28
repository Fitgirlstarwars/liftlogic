"""
LLM Service - Unified language model interface.

Routes between:
- Gemini (user's OAuth token → user's quota → zero cost)
- Ollama (local fallback → your server costs)

Architecture:
    User Authenticated → Gemini with user's token
    Not Authenticated → Ollama local model
    Gemini Quota Exceeded → Ollama fallback
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

from liftlogic.config import LLMError, get_settings

if TYPE_CHECKING:
    from liftlogic.interfaces.api.auth import UserContext

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM generation."""

    text: str
    model: str
    provider: str  # "gemini" or "ollama"
    tokens_used: int | None = None


class LLMService:
    """
    Unified LLM service supporting Gemini (user OAuth) and Ollama (fallback).

    Example:
        >>> # With user auth (uses Gemini with their quota)
        >>> llm = LLMService(user_token="ya29.xxx")
        >>> response = await llm.generate("Explain fault code F505")

        >>> # Without auth (uses Ollama)
        >>> llm = LLMService()
        >>> response = await llm.generate("Explain fault code F505")
    """

    def __init__(
        self,
        user_token: str | None = None,
        model: str | None = None,
    ) -> None:
        """
        Initialize LLM service.

        Args:
            user_token: User's Google OAuth access token (for Gemini)
            model: Override default model
        """
        self.settings = get_settings()
        self.user_token = user_token
        self.model = model or self.settings.gemini_model

        # Determine provider based on auth
        if user_token:
            self.provider = "gemini"
            logger.debug("LLM: Using Gemini with user OAuth token")
        else:
            self.provider = "ollama"
            logger.debug("LLM: Using Ollama (no user auth)")

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        """
        Generate text response.

        Args:
            prompt: User prompt
            system_instruction: System prompt
            temperature: Override default temperature

        Returns:
            LLMResponse with generated text
        """
        if self.provider == "gemini":
            try:
                return await self._generate_gemini(prompt, system_instruction, temperature)
            except Exception as e:
                logger.warning("Gemini failed, falling back to Ollama: %s", e)
                return await self._generate_ollama(prompt, system_instruction, temperature)
        else:
            return await self._generate_ollama(prompt, system_instruction, temperature)

    async def _generate_gemini(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Generate using Gemini with user's OAuth token."""
        if not self.user_token:
            raise LLMError("No user token for Gemini")

        # Build request
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        )

        contents = []
        if system_instruction:
            contents.append({"role": "user", "parts": [{"text": system_instruction}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature or self.settings.gemini_temperature,
            },
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.user_token}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=60.0,
            )

            if response.status_code == 429:
                raise LLMError("Gemini quota exceeded", {"code": "QUOTA_EXCEEDED"})

            if response.status_code != 200:
                logger.error("Gemini error: %s %s", response.status_code, response.text)
                raise LLMError(f"Gemini API error: {response.status_code}")

            data = response.json()

            # Extract text from response
            text = ""
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text = parts[0].get("text", "")

            # Get token usage
            usage = data.get("usageMetadata", {})
            tokens = usage.get("totalTokenCount")

            return LLMResponse(
                text=text,
                model=self.model,
                provider="gemini",
                tokens_used=tokens,
            )

    async def _generate_ollama(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Generate using local Ollama."""
        url = f"{self.settings.ollama_url}/api/generate"

        full_prompt = prompt
        if system_instruction:
            full_prompt = f"{system_instruction}\n\n{prompt}"

        body = {
            "model": self.settings.ollama_model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature or self.settings.gemini_temperature,
            },
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=body, timeout=120.0)

                if response.status_code != 200:
                    raise LLMError(f"Ollama error: {response.status_code}")

                data = response.json()

                return LLMResponse(
                    text=data.get("response", ""),
                    model=self.settings.ollama_model,
                    provider="ollama",
                    tokens_used=data.get("eval_count"),
                )

        except httpx.ConnectError:
            raise LLMError(
                "Ollama not running. Start with: ollama serve",
                {"hint": "Run 'ollama serve' in a terminal"},
            )

    async def generate_json(
        self,
        prompt: str,
        system_instruction: str | None = None,
    ) -> dict[str, Any]:
        """Generate JSON response."""
        json_instruction = (system_instruction or "") + "\n\nRespond with valid JSON only."

        response = await self.generate(prompt, json_instruction)

        import json

        try:
            result: dict[str, Any] = json.loads(response.text)
            return result
        except json.JSONDecodeError:
            # Try to extract JSON from response
            text = response.text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(text[start:end])
                return result
            raise


async def get_llm_for_user(user: UserContext | None) -> LLMService:
    """
    Get LLM service configured for user.

    Args:
        user: Authenticated user context (or None for fallback)

    Returns:
        LLMService configured with user's token or Ollama fallback
    """
    if user and user.access_token:
        return LLMService(user_token=user.access_token)
    return LLMService()

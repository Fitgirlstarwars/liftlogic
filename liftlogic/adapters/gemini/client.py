"""
Gemini Client - Unified Google Gemini API client.

This is the SINGLE source of truth for all Gemini API interactions.

Authentication:
- Uses OAuth/ADC (Application Default Credentials) - NO API KEY REQUIRED
- Run `gcloud auth application-default login` once to authenticate
- Zero API cost via Google AI Ultra quota

Features:
- Async operations with connection pooling
- Rate limiting (60 RPM default)
- Automatic retries with exponential backoff
- File API for large documents (up to 2M tokens)
- Thinking mode configuration
- Response streaming support
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, AsyncIterator

import google.generativeai as genai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .models import (
    GeminiConfig,
    GeminiRequest,
    GeminiResponse,
    ExtractionRequest,
    ExtractionResponse,
    ThinkingLevel,
)

logger = logging.getLogger(__name__)

__all__ = ["GeminiClient", "RateLimitError", "GeminiAPIError"]


class RateLimitError(Exception):
    """Rate limit exceeded."""

    pass


class GeminiAPIError(Exception):
    """Gemini API error."""

    pass


class GeminiClient:
    """
    Unified Gemini API client using OAuth/ADC (zero API cost).

    Setup:
        1. Install gcloud CLI: https://cloud.google.com/sdk/docs/install
        2. Run: gcloud auth application-default login
        3. Use the client - no API key needed!

    Example:
        >>> client = GeminiClient()  # Uses OAuth/ADC automatically
        >>> response = await client.generate("What is fault code 505?")
        >>> print(response.text)

        >>> # For PDF extraction
        >>> result = await client.extract_pdf("manual.pdf")
        >>> print(result.fault_codes)
    """

    def __init__(
        self,
        config: GeminiConfig | None = None,
    ) -> None:
        """
        Initialize Gemini client with OAuth/ADC.

        No API key required - uses Application Default Credentials.
        Run `gcloud auth application-default login` to authenticate.

        Args:
            config: Client configuration. Uses defaults if None.
        """
        self.config = config or GeminiConfig()

        # OAuth/ADC: Don't configure API key - library uses ADC automatically
        # User must run: gcloud auth application-default login

        # Rate limiting state
        self._request_times: list[float] = []
        self._rate_lock = asyncio.Lock()

        # Model instance (lazy loaded)
        self._model: genai.GenerativeModel | None = None

        logger.info(
            "GeminiClient initialized (OAuth/ADC mode): model=%s, thinking=%s",
            self.config.model,
            self.config.thinking_level.value,
        )

    def _get_model(self) -> genai.GenerativeModel:
        """Get or create model instance."""
        if self._model is None:
            generation_config: dict[str, Any] = {
                "temperature": self.config.temperature,
                "max_output_tokens": self.config.max_output_tokens,
            }

            # Add thinking config for Gemini 2.0+
            if "2.0" in self.config.model or "3" in self.config.model:
                if self.config.thinking_level != ThinkingLevel.NONE:
                    generation_config["thinking_config"] = {
                        "thinking_budget": self._thinking_budget()
                    }

            self._model = genai.GenerativeModel(
                model_name=self.config.model,
                generation_config=generation_config,
            )
        return self._model

    def _thinking_budget(self) -> int:
        """Get thinking token budget based on level."""
        budgets = {
            ThinkingLevel.NONE: 0,
            ThinkingLevel.LOW: 1024,
            ThinkingLevel.MEDIUM: 4096,
            ThinkingLevel.HIGH: 16384,
        }
        return budgets.get(self.config.thinking_level, 8192)

    async def _check_rate_limit(self) -> None:
        """Enforce rate limiting."""
        async with self._rate_lock:
            now = time.time()
            # Remove requests older than 1 minute
            self._request_times = [t for t in self._request_times if now - t < 60]

            if len(self._request_times) >= self.config.rate_limit_rpm:
                wait_time = 60 - (now - self._request_times[0])
                if wait_time > 0:
                    logger.warning("Rate limit reached, waiting %.1fs", wait_time)
                    await asyncio.sleep(wait_time)

            self._request_times.append(now)

    @retry(
        retry=retry_if_exception_type((GeminiAPIError, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
    )
    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        response_mime_type: str = "text/plain",
    ) -> GeminiResponse:
        """
        Generate text from prompt.

        Args:
            prompt: User prompt
            system_instruction: Optional system instruction
            response_mime_type: Response format ("text/plain" or "application/json")

        Returns:
            GeminiResponse with generated text

        Raises:
            GeminiAPIError: API call failed
            RateLimitError: Rate limit exceeded
        """
        await self._check_rate_limit()

        try:
            model = self._get_model()

            # Build content
            contents = []
            if system_instruction:
                contents.append({"role": "user", "parts": [system_instruction]})
                contents.append({"role": "model", "parts": ["Understood."]})
            contents.append({"role": "user", "parts": [prompt]})

            # Generate
            response = await asyncio.to_thread(
                model.generate_content,
                contents,
                request_options={"timeout": self.config.timeout_seconds},
            )

            # Parse response
            text = response.text if hasattr(response, "text") else str(response)

            # Get usage stats
            usage = getattr(response, "usage_metadata", None)
            prompt_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
            completion_tokens = (
                getattr(usage, "candidates_token_count", 0) if usage else 0
            )

            return GeminiResponse(
                text=text,
                model=self.config.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )

        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "rate" in error_msg:
                raise RateLimitError(f"Rate limit exceeded: {e}") from e
            raise GeminiAPIError(f"Gemini API error: {e}") from e

    async def generate_json(
        self,
        prompt: str,
        system_instruction: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate JSON response.

        Args:
            prompt: User prompt
            system_instruction: Optional system instruction

        Returns:
            Parsed JSON dict
        """
        response = await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            response_mime_type="application/json",
        )

        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            text = response.text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            raise

    async def upload_file(self, file_path: str | Path) -> genai.File:
        """
        Upload file to Gemini File API.

        Args:
            file_path: Path to file

        Returns:
            Uploaded file object
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info("Uploading file: %s", file_path.name)

        file = await asyncio.to_thread(genai.upload_file, str(file_path))

        # Wait for processing
        while file.state.name == "PROCESSING":
            logger.debug("File processing...")
            await asyncio.sleep(2)
            file = await asyncio.to_thread(genai.get_file, file.name)

        if file.state.name == "FAILED":
            raise GeminiAPIError(f"File processing failed: {file.state.name}")

        logger.info("File uploaded: %s", file.uri)
        return file

    async def delete_file(self, file: genai.File) -> None:
        """Delete uploaded file."""
        try:
            await asyncio.to_thread(genai.delete_file, file.name)
            logger.debug("Deleted file: %s", file.name)
        except Exception as e:
            logger.warning("Failed to delete file %s: %s", file.name, e)

    async def extract_pdf(
        self,
        pdf_path: str | Path,
        request: ExtractionRequest | None = None,
    ) -> ExtractionResponse:
        """
        Extract structured data from PDF.

        Args:
            pdf_path: Path to PDF file
            request: Extraction configuration

        Returns:
            ExtractionResponse with components, connections, fault codes, etc.
        """
        pdf_path = Path(pdf_path)
        request = request or ExtractionRequest(pdf_path=str(pdf_path))

        # Build extraction prompt
        prompt = self._build_extraction_prompt(request)

        # Upload file
        uploaded_file = await self.upload_file(pdf_path)

        try:
            await self._check_rate_limit()

            model = self._get_model()

            # Generate with file
            response = await asyncio.to_thread(
                model.generate_content,
                [uploaded_file, prompt],
                request_options={"timeout": self.config.timeout_seconds},
            )

            # Parse response
            result = self._parse_extraction_response(response.text, pdf_path)
            return result

        finally:
            await self.delete_file(uploaded_file)

    def _build_extraction_prompt(self, request: ExtractionRequest) -> str:
        """Build extraction prompt based on request."""
        sections = ["Extract the following from this technical manual:"]

        if request.extract_fault_codes:
            sections.append(
                "- FAULT CODES: code, description, severity, causes, remedies"
            )
        if request.extract_tables:
            sections.append("- TABLES: title, headers, rows")
        if request.extract_schematics:
            sections.append(
                "- COMPONENTS: id, name, type, specifications"
            )
            sections.append(
                "- CONNECTIONS: source component, target component, type, label"
            )

        sections.append(
            "\nReturn as JSON with keys: fault_codes, tables, components, connections, metadata"
        )

        return "\n".join(sections)

    def _parse_extraction_response(
        self, text: str, pdf_path: Path
    ) -> ExtractionResponse:
        """Parse extraction response into structured format."""
        try:
            # Try to parse as JSON
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
            else:
                data = {}
        except json.JSONDecodeError:
            data = {}
            logger.warning("Failed to parse extraction response as JSON")

        return ExtractionResponse(
            source_file=str(pdf_path),
            components=data.get("components", []),
            connections=data.get("connections", []),
            fault_codes=data.get("fault_codes", []),
            tables=data.get("tables", []),
            metadata=data.get("metadata", {}),
        )

    async def stream_generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream generated text.

        Args:
            prompt: User prompt
            system_instruction: Optional system instruction

        Yields:
            Text chunks as they're generated
        """
        await self._check_rate_limit()

        model = self._get_model()

        contents = []
        if system_instruction:
            contents.append({"role": "user", "parts": [system_instruction]})
            contents.append({"role": "model", "parts": ["Understood."]})
        contents.append({"role": "user", "parts": [prompt]})

        response = await asyncio.to_thread(
            model.generate_content,
            contents,
            stream=True,
            request_options={"timeout": self.config.timeout_seconds},
        )

        for chunk in response:
            if hasattr(chunk, "text"):
                yield chunk.text

"""
Gemini Models - Request/Response types for Gemini API.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ThinkingLevel(str, Enum):
    """Gemini 3 thinking mode levels."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GeminiConfig(BaseModel):
    """Configuration for Gemini client."""

    model: str = Field(default="gemini-2.0-flash")
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    thinking_level: ThinkingLevel = Field(default=ThinkingLevel.HIGH)
    max_output_tokens: int = Field(default=8192)
    timeout_seconds: int = Field(default=300)
    max_retries: int = Field(default=3)
    rate_limit_rpm: int = Field(default=60)

    model_config = {"frozen": True}


class GeminiRequest(BaseModel):
    """Generic Gemini API request."""

    prompt: str
    system_instruction: str | None = None
    response_mime_type: str = Field(default="text/plain")
    config: GeminiConfig = Field(default_factory=GeminiConfig)

    model_config = {"frozen": True}


class GeminiResponse(BaseModel):
    """Generic Gemini API response."""

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    thinking_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = "STOP"

    @property
    def total_cost(self) -> float:
        """Estimate cost (Gemini 3 Pro pricing placeholder)."""
        # Adjust when pricing is finalized
        return 0.0


class ExtractionRequest(BaseModel):
    """Request for PDF extraction."""

    pdf_path: str
    extract_tables: bool = True
    extract_schematics: bool = True
    extract_fault_codes: bool = True
    thinking_level: ThinkingLevel = ThinkingLevel.HIGH

    model_config = {"frozen": True}


class Component(BaseModel):
    """Extracted component from schematic."""

    id: str
    name: str
    type: str | None = None
    specs: dict[str, Any] = Field(default_factory=dict)


class Connection(BaseModel):
    """Connection between components."""

    source: str
    target: str
    type: str = "electrical"
    label: str | None = None


class FaultCode(BaseModel):
    """Extracted fault code."""

    code: str
    description: str
    severity: str | None = None
    causes: list[str] = Field(default_factory=list)
    remedies: list[str] = Field(default_factory=list)


class Table(BaseModel):
    """Extracted table."""

    title: str | None = None
    headers: list[str] = Field(default_factory=list)
    rows: list[dict[str, str]] = Field(default_factory=list)
    page: int = 0


class ExtractionResponse(BaseModel):
    """Response from PDF extraction."""

    source_file: str
    page_count: int = 0
    components: list[Component] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    fault_codes: list[FaultCode] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    text_content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    quality_score: float = 0.0

"""
Extraction Models - Data types for extraction domain.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


class PDFDocument(BaseModel):
    """Input document for extraction."""

    path: Path
    filename: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    document_type: str | None = None

    model_config = {"frozen": True}

    @model_validator(mode="before")
    @classmethod
    def set_filename_from_path(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Set filename from path if not provided."""
        if isinstance(data, dict):
            if data.get("filename") is None and "path" in data:
                path = data["path"]
                if isinstance(path, str):
                    path = Path(path)
                data["filename"] = path.name
        return data


class ExtractedComponent(BaseModel):
    """Extracted component from schematic."""

    id: str
    name: str
    type: str | None = None
    manufacturer: str | None = None
    part_number: str | None = None
    specs: dict[str, Any] = Field(default_factory=dict)
    page: int = 0
    confidence: float = 1.0


class ExtractedConnection(BaseModel):
    """Connection between components."""

    source_id: str
    target_id: str
    connection_type: str = "electrical"
    label: str | None = None
    wire_color: str | None = None
    terminal_from: str | None = None
    terminal_to: str | None = None
    page: int = 0
    confidence: float = 1.0


class ExtractedFaultCode(BaseModel):
    """Extracted fault code information."""

    code: str
    description: str
    severity: str | None = None  # "critical", "warning", "info"
    causes: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    remedies: list[str] = Field(default_factory=list)
    related_components: list[str] = Field(default_factory=list)
    page: int = 0
    confidence: float = 1.0


class ExtractedTable(BaseModel):
    """Extracted table data."""

    title: str | None = None
    headers: list[str] = Field(default_factory=list)
    rows: list[dict[str, str]] = Field(default_factory=list)
    page: int = 0
    table_type: str | None = None  # "specifications", "fault_codes", "wiring", etc.


class DocumentMetadata(BaseModel):
    """Document metadata extracted from PDF."""

    title: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    document_type: str | None = None  # "service_manual", "installation", "parts_list"
    revision: str | None = None
    date: str | None = None
    language: str = "en"
    page_count: int = 0


class QualityScore(BaseModel):
    """Quality evaluation scores."""

    faithfulness: float = Field(ge=0.0, le=1.0, description="Accuracy to source")
    completeness: float = Field(ge=0.0, le=1.0, description="Coverage of content")
    consistency: float = Field(ge=0.0, le=1.0, description="Internal consistency")
    overall: float = Field(ge=0.0, le=1.0, description="Overall quality score")
    issues: list[str] = Field(default_factory=list)

    @classmethod
    def compute_overall(
        cls,
        faithfulness: float,
        completeness: float,
        consistency: float,
    ) -> "QualityScore":
        """Compute overall score from individual metrics."""
        overall = (faithfulness * 0.5 + completeness * 0.3 + consistency * 0.2)
        return cls(
            faithfulness=faithfulness,
            completeness=completeness,
            consistency=consistency,
            overall=overall,
        )


class ExtractionResult(BaseModel):
    """Complete extraction result from a PDF."""

    # Source information
    source_file: str
    source_path: Path | None = None

    # Extracted content
    components: list[ExtractedComponent] = Field(default_factory=list)
    connections: list[ExtractedConnection] = Field(default_factory=list)
    fault_codes: list[ExtractedFaultCode] = Field(default_factory=list)
    tables: list[ExtractedTable] = Field(default_factory=list)
    text_content: str = ""

    # Metadata
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    quality: QualityScore | None = None

    # Processing info
    extraction_time: datetime = Field(default_factory=datetime.now)
    processing_seconds: float = 0.0
    model_used: str = ""
    token_count: int = 0

    @property
    def component_count(self) -> int:
        """Total number of components."""
        return len(self.components)

    @property
    def fault_code_count(self) -> int:
        """Total number of fault codes."""
        return len(self.fault_codes)

    @property
    def has_quality_issues(self) -> bool:
        """Check if extraction has quality issues."""
        if self.quality is None:
            return False
        return self.quality.overall < 0.7 or len(self.quality.issues) > 0

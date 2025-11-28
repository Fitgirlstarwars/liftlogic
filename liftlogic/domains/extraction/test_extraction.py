"""
Tests for extraction domain models and extractor.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from .extractor import GeminiExtractor
from .models import (
    DocumentMetadata,
    ExtractedComponent,
    ExtractedConnection,
    ExtractedFaultCode,
    ExtractedTable,
    ExtractionResult,
    PDFDocument,
    QualityScore,
)


# --- PDFDocument Tests ---


def test_pdf_document_basic() -> None:
    """Test PDFDocument with basic path."""
    doc = PDFDocument(path=Path("/test/manual.pdf"))
    assert doc.path == Path("/test/manual.pdf")
    assert doc.filename == "manual.pdf"  # Auto-set from path


def test_pdf_document_with_filename() -> None:
    """Test PDFDocument with explicit filename."""
    doc = PDFDocument(path=Path("/test/file.pdf"), filename="custom_name.pdf")
    assert doc.filename == "custom_name.pdf"


def test_pdf_document_with_metadata() -> None:
    """Test PDFDocument with all metadata."""
    doc = PDFDocument(
        path=Path("/test/manual.pdf"),
        manufacturer="KONE",
        model="EcoSpace",
        document_type="service_manual",
    )
    assert doc.manufacturer == "KONE"
    assert doc.model == "EcoSpace"
    assert doc.document_type == "service_manual"


def test_pdf_document_string_path() -> None:
    """Test PDFDocument accepts string path."""
    doc = PDFDocument(path="/test/manual.pdf")  # type: ignore
    assert doc.path == Path("/test/manual.pdf")
    assert doc.filename == "manual.pdf"


def test_pdf_document_is_immutable() -> None:
    """Test PDFDocument is frozen/immutable."""
    doc = PDFDocument(path=Path("/test/manual.pdf"))
    with pytest.raises(Exception):  # ValidationError for frozen model
        doc.filename = "changed.pdf"  # type: ignore


# --- ExtractedComponent Tests ---


def test_extracted_component_basic() -> None:
    """Test ExtractedComponent with required fields."""
    component = ExtractedComponent(id="K1", name="Door Relay")
    assert component.id == "K1"
    assert component.name == "Door Relay"
    assert component.type is None
    assert component.specs == {}
    assert component.confidence == 1.0


def test_extracted_component_full() -> None:
    """Test ExtractedComponent with all fields."""
    component = ExtractedComponent(
        id="IGBT505",
        name="Inverter IGBT Module",
        type="semiconductor",
        manufacturer="Infineon",
        part_number="BSM100GAR120DN2",
        specs={"voltage": 1200, "current": 100},
        page=45,
        confidence=0.95,
    )
    assert component.id == "IGBT505"
    assert component.type == "semiconductor"
    assert component.specs["voltage"] == 1200
    assert component.confidence == 0.95


# --- ExtractedConnection Tests ---


def test_extracted_connection_basic() -> None:
    """Test ExtractedConnection with required fields."""
    conn = ExtractedConnection(source_id="K1", target_id="K2")
    assert conn.source_id == "K1"
    assert conn.target_id == "K2"
    assert conn.connection_type == "electrical"


def test_extracted_connection_full() -> None:
    """Test ExtractedConnection with all fields."""
    conn = ExtractedConnection(
        source_id="K1",
        target_id="M1",
        connection_type="power",
        label="Motor Power",
        wire_color="blue",
        terminal_from="13",
        terminal_to="U1",
        page=12,
        confidence=0.85,
    )
    assert conn.label == "Motor Power"
    assert conn.wire_color == "blue"


# --- ExtractedFaultCode Tests ---


def test_extracted_fault_code_basic() -> None:
    """Test ExtractedFaultCode with required fields."""
    fault = ExtractedFaultCode(code="F505", description="Door fault")
    assert fault.code == "F505"
    assert fault.description == "Door fault"
    assert fault.causes == []
    assert fault.remedies == []


def test_extracted_fault_code_full() -> None:
    """Test ExtractedFaultCode with all fields."""
    fault = ExtractedFaultCode(
        code="F505",
        description="Door zone sensor malfunction",
        severity="warning",
        causes=["Dirty sensor", "Misalignment"],
        symptoms=["Door won't close", "Intermittent errors"],
        remedies=["Clean sensor", "Realign sensor"],
        related_components=["K1", "DZS1"],
        page=23,
        confidence=0.9,
    )
    assert fault.severity == "warning"
    assert len(fault.causes) == 2
    assert "K1" in fault.related_components


# --- ExtractedTable Tests ---


def test_extracted_table() -> None:
    """Test ExtractedTable model."""
    table = ExtractedTable(
        title="Fault Code Reference",
        headers=["Code", "Description", "Severity"],
        rows=[
            {"Code": "F505", "Description": "Door fault", "Severity": "Warning"},
            {"Code": "F101", "Description": "Speed fault", "Severity": "Critical"},
        ],
        page=10,
        table_type="fault_codes",
    )
    assert table.title == "Fault Code Reference"
    assert len(table.rows) == 2
    assert table.table_type == "fault_codes"


# --- DocumentMetadata Tests ---


def test_document_metadata_defaults() -> None:
    """Test DocumentMetadata default values."""
    meta = DocumentMetadata()
    assert meta.title is None
    assert meta.language == "en"
    assert meta.page_count == 0


def test_document_metadata_full() -> None:
    """Test DocumentMetadata with all fields."""
    meta = DocumentMetadata(
        title="KONE EcoSpace Service Manual",
        manufacturer="KONE",
        model="EcoSpace",
        document_type="service_manual",
        revision="2.3",
        date="2024-01",
        page_count=450,
    )
    assert meta.title == "KONE EcoSpace Service Manual"
    assert meta.page_count == 450


# --- QualityScore Tests ---


def test_quality_score_validation() -> None:
    """Test QualityScore validates ranges."""
    score = QualityScore(
        faithfulness=0.9,
        completeness=0.8,
        consistency=0.85,
        overall=0.87,
    )
    assert score.faithfulness == 0.9

    # Invalid scores should raise
    with pytest.raises(ValueError):
        QualityScore(faithfulness=1.5, completeness=0.8, consistency=0.85, overall=0.87)

    with pytest.raises(ValueError):
        QualityScore(faithfulness=-0.1, completeness=0.8, consistency=0.85, overall=0.87)


def test_quality_score_compute_overall() -> None:
    """Test QualityScore.compute_overall calculation."""
    score = QualityScore.compute_overall(
        faithfulness=0.9,  # 0.9 * 0.5 = 0.45
        completeness=0.8,  # 0.8 * 0.3 = 0.24
        consistency=0.7,  # 0.7 * 0.2 = 0.14
    )
    # Overall = 0.45 + 0.24 + 0.14 = 0.83
    assert score.overall == pytest.approx(0.83)


def test_quality_score_with_issues() -> None:
    """Test QualityScore with quality issues."""
    score = QualityScore(
        faithfulness=0.9,
        completeness=0.8,
        consistency=0.85,
        overall=0.87,
        issues=["Missing some fault codes", "Table extraction incomplete"],
    )
    assert len(score.issues) == 2


# --- ExtractionResult Tests ---


def test_extraction_result_basic() -> None:
    """Test ExtractionResult with minimal data."""
    result = ExtractionResult(source_file="manual.pdf")
    assert result.source_file == "manual.pdf"
    assert result.components == []
    assert result.component_count == 0
    assert result.fault_code_count == 0


def test_extraction_result_with_data() -> None:
    """Test ExtractionResult with extracted data."""
    result = ExtractionResult(
        source_file="manual.pdf",
        source_path=Path("/test/manual.pdf"),
        components=[
            ExtractedComponent(id="K1", name="Relay 1"),
            ExtractedComponent(id="K2", name="Relay 2"),
        ],
        fault_codes=[
            ExtractedFaultCode(code="F505", description="Door fault"),
        ],
        processing_seconds=5.2,
        model_used="gemini-2.0-flash",
    )
    assert result.component_count == 2
    assert result.fault_code_count == 1
    assert result.processing_seconds == 5.2


def test_extraction_result_has_quality_issues() -> None:
    """Test ExtractionResult.has_quality_issues property."""
    # No quality score
    result = ExtractionResult(source_file="manual.pdf")
    assert result.has_quality_issues is False

    # Good quality
    result_good = ExtractionResult(
        source_file="manual.pdf",
        quality=QualityScore(
            faithfulness=0.9, completeness=0.85, consistency=0.9, overall=0.88
        ),
    )
    assert result_good.has_quality_issues is False

    # Low overall score
    result_low = ExtractionResult(
        source_file="manual.pdf",
        quality=QualityScore(
            faithfulness=0.5, completeness=0.5, consistency=0.5, overall=0.5
        ),
    )
    assert result_low.has_quality_issues is True

    # Has issues list
    result_issues = ExtractionResult(
        source_file="manual.pdf",
        quality=QualityScore(
            faithfulness=0.9,
            completeness=0.85,
            consistency=0.9,
            overall=0.88,
            issues=["Missing diagrams"],
        ),
    )
    assert result_issues.has_quality_issues is True


# --- GeminiExtractor Tests ---


@pytest.fixture
def mock_gemini_client() -> AsyncMock:
    """Create a mock GeminiClient."""
    mock = AsyncMock()
    mock.config = MagicMock()
    mock.config.model = "gemini-2.0-flash"

    # Mock upload_file
    mock_file = MagicMock()
    mock.upload_file.return_value = mock_file
    mock.delete_file.return_value = None

    # Mock generate_json with extraction response
    mock.generate_json.return_value = {
        "components": [
            {"id": "K1", "name": "Door Relay", "type": "relay"},
        ],
        "connections": [
            {"source_id": "K1", "target_id": "K2", "connection_type": "signal"},
        ],
        "fault_codes": [
            {
                "code": "F505",
                "description": "Door fault",
                "severity": "warning",
                "causes": ["Dirty sensor"],
            },
        ],
        "tables": [],
        "metadata": {
            "title": "Test Manual",
            "manufacturer": "KONE",
        },
    }

    return mock


@pytest.fixture
def extractor(mock_gemini_client: AsyncMock) -> GeminiExtractor:
    """Create a GeminiExtractor with mocked client."""
    return GeminiExtractor(mock_gemini_client)


async def test_extractor_extract(
    extractor: GeminiExtractor, mock_gemini_client: AsyncMock, tmp_path: Path
) -> None:
    """Test GeminiExtractor.extract method."""
    # Create test PDF file
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    doc = PDFDocument(path=pdf_path)
    result = await extractor.extract(doc)

    assert result.source_file == "test.pdf"
    assert result.component_count == 1
    assert result.fault_code_count == 1
    assert result.model_used == "gemini-2.0-flash"

    # Verify upload and delete were called
    mock_gemini_client.upload_file.assert_called_once()
    mock_gemini_client.delete_file.assert_called_once()


async def test_extractor_extract_batch(
    extractor: GeminiExtractor, mock_gemini_client: AsyncMock, tmp_path: Path
) -> None:
    """Test GeminiExtractor.extract_batch method."""
    # Create test PDF files
    pdf1 = tmp_path / "test1.pdf"
    pdf2 = tmp_path / "test2.pdf"
    pdf1.write_bytes(b"%PDF-1.4 test1")
    pdf2.write_bytes(b"%PDF-1.4 test2")

    docs = [PDFDocument(path=pdf1), PDFDocument(path=pdf2)]
    results = await extractor.extract_batch(docs, max_concurrent=2)

    assert len(results) == 2


async def test_extractor_handles_extraction_error(
    extractor: GeminiExtractor, mock_gemini_client: AsyncMock, tmp_path: Path
) -> None:
    """Test extractor handles errors gracefully in batch."""
    # First call succeeds, second fails
    mock_gemini_client.generate_json.side_effect = [
        {
            "components": [],
            "connections": [],
            "fault_codes": [],
            "tables": [],
            "metadata": {},
        },
        Exception("Extraction failed"),
    ]

    pdf1 = tmp_path / "test1.pdf"
    pdf2 = tmp_path / "test2.pdf"
    pdf1.write_bytes(b"%PDF-1.4 test1")
    pdf2.write_bytes(b"%PDF-1.4 test2")

    docs = [PDFDocument(path=pdf1), PDFDocument(path=pdf2)]
    results = await extractor.extract_batch(docs)

    # Only successful extractions returned
    assert len(results) == 1

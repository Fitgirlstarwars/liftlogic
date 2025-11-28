"""
Extraction Domain - PDF to structured data extraction.

This domain handles:
- PDF document processing
- Fault code extraction
- Component and schematic analysis
- Table extraction
- Quality evaluation
"""

from .contracts import Extractor, QualityEvaluator
from .models import (
    ExtractionResult,
    PDFDocument,
    ExtractedComponent,
    ExtractedConnection,
    ExtractedFaultCode,
    ExtractedTable,
)
from .extractor import GeminiExtractor
from .evaluator import ExtractionEvaluator

__all__ = [
    # Contracts
    "Extractor",
    "QualityEvaluator",
    # Models
    "ExtractionResult",
    "PDFDocument",
    "ExtractedComponent",
    "ExtractedConnection",
    "ExtractedFaultCode",
    "ExtractedTable",
    # Implementations
    "GeminiExtractor",
    "ExtractionEvaluator",
]

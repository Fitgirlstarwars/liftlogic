"""
Extraction Contracts - Interfaces for extraction domain.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import ExtractionResult, PDFDocument, QualityScore


@runtime_checkable
class Extractor(Protocol):
    """
    Contract for PDF extraction implementations.

    Example:
        >>> class MyExtractor:
        ...     async def extract(self, document: PDFDocument) -> ExtractionResult:
        ...         ...
        >>> assert isinstance(MyExtractor(), Extractor)
    """

    async def extract(self, document: PDFDocument) -> ExtractionResult:
        """
        Extract structured data from a PDF document.

        Args:
            document: PDF document to process

        Returns:
            Extraction result with components, connections, fault codes, etc.
        """
        ...

    async def extract_batch(
        self,
        documents: list[PDFDocument],
        max_concurrent: int = 5,
    ) -> list[ExtractionResult]:
        """
        Extract from multiple documents in parallel.

        Args:
            documents: List of documents to process
            max_concurrent: Maximum concurrent extractions

        Returns:
            List of extraction results
        """
        ...


@runtime_checkable
class QualityEvaluator(Protocol):
    """
    Contract for extraction quality evaluation.

    Example:
        >>> class MyEvaluator:
        ...     async def evaluate(self, result: ExtractionResult, source: str) -> QualityScore:
        ...         ...
    """

    async def evaluate(
        self,
        result: ExtractionResult,
        source_text: str,
    ) -> QualityScore:
        """
        Evaluate extraction quality.

        Args:
            result: Extraction result to evaluate
            source_text: Original source text for comparison

        Returns:
            Quality scores
        """
        ...

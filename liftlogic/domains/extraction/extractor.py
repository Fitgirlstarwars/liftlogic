"""
Gemini Extractor - PDF extraction using Gemini API.

This is the main extraction implementation that processes PDF documents
and extracts structured data using Google Gemini.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from .models import (
    ExtractionResult,
    PDFDocument,
    ExtractedComponent,
    ExtractedConnection,
    ExtractedFaultCode,
    ExtractedTable,
    DocumentMetadata,
)

if TYPE_CHECKING:
    from liftlogic.adapters.gemini import GeminiClient

logger = logging.getLogger(__name__)

__all__ = ["GeminiExtractor"]

EXTRACTION_PROMPT = """Analyze this technical elevator/lift manual and extract:

1. FAULT CODES: For each fault code found, extract:
   - code: The fault code identifier (e.g., "505", "E-01", "F123")
   - description: What the fault means
   - severity: "critical", "warning", or "info"
   - causes: List of possible causes
   - symptoms: List of symptoms indicating this fault
   - remedies: List of repair/resolution steps
   - related_components: Components involved

2. COMPONENTS: For each component in schematics/diagrams:
   - id: Unique identifier (e.g., "K1", "IGBT505", "M1")
   - name: Component name
   - type: Component type (relay, motor, sensor, etc.)
   - specs: Any specifications mentioned

3. CONNECTIONS: For wiring/connections between components:
   - source_id: Source component ID
   - target_id: Target component ID
   - connection_type: "electrical", "mechanical", "signal"
   - label: Connection label if any

4. TABLES: For specification or data tables:
   - title: Table title
   - headers: Column headers
   - rows: Data rows as objects

5. METADATA: Document information:
   - title: Document title
   - manufacturer: Equipment manufacturer
   - model: Equipment model
   - document_type: "service_manual", "installation", "parts_list"

Return as JSON with keys: fault_codes, components, connections, tables, metadata"""


class GeminiExtractor:
    """
    PDF extractor using Gemini API.

    Example:
        >>> from liftlogic.adapters.gemini import GeminiClient
        >>> client = GeminiClient()
        >>> extractor = GeminiExtractor(client)
        >>> result = await extractor.extract(PDFDocument(path=Path("manual.pdf")))
    """

    def __init__(self, client: GeminiClient) -> None:
        """
        Initialize extractor.

        Args:
            client: Gemini API client
        """
        self._client = client

    async def extract(self, document: PDFDocument) -> ExtractionResult:
        """
        Extract structured data from PDF.

        Args:
            document: PDF document to process

        Returns:
            Extraction result with all extracted data
        """
        start_time = time.time()
        logger.info("Starting extraction: %s", document.filename)

        # Upload and process with Gemini
        uploaded_file = await self._client.upload_file(document.path)

        try:
            # Generate extraction
            response = await self._client.generate_json(
                prompt=EXTRACTION_PROMPT,
                system_instruction="You are an expert elevator technical documentation analyzer.",
            )

            # Parse response into structured models
            result = self._parse_response(response, document)
            result.processing_seconds = time.time() - start_time
            result.model_used = self._client.config.model

            logger.info(
                "Extraction complete: %s - %d components, %d fault codes in %.1fs",
                document.filename,
                result.component_count,
                result.fault_code_count,
                result.processing_seconds,
            )

            return result

        finally:
            await self._client.delete_file(uploaded_file)

    async def extract_batch(
        self,
        documents: list[PDFDocument],
        max_concurrent: int = 5,
    ) -> list[ExtractionResult]:
        """
        Extract from multiple documents in parallel.

        Args:
            documents: List of documents
            max_concurrent: Maximum concurrent extractions

        Returns:
            List of extraction results
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def extract_with_limit(doc: PDFDocument) -> ExtractionResult:
            async with semaphore:
                return await self.extract(doc)

        tasks = [extract_with_limit(doc) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and log them
        valid_results = []
        for doc, result in zip(documents, results):
            if isinstance(result, Exception):
                logger.error("Failed to extract %s: %s", doc.filename, result)
            else:
                valid_results.append(result)

        return valid_results

    def _parse_response(
        self,
        response: dict,
        document: PDFDocument,
    ) -> ExtractionResult:
        """Parse Gemini response into structured models."""

        # Parse components
        components = [
            ExtractedComponent(**c) for c in response.get("components", [])
        ]

        # Parse connections
        connections = [
            ExtractedConnection(**c) for c in response.get("connections", [])
        ]

        # Parse fault codes
        fault_codes = [
            ExtractedFaultCode(**f) for f in response.get("fault_codes", [])
        ]

        # Parse tables
        tables = [
            ExtractedTable(**t) for t in response.get("tables", [])
        ]

        # Parse metadata
        meta_data = response.get("metadata", {})
        metadata = DocumentMetadata(
            title=meta_data.get("title"),
            manufacturer=meta_data.get("manufacturer") or document.manufacturer,
            model=meta_data.get("model") or document.model,
            document_type=meta_data.get("document_type") or document.document_type,
        )

        return ExtractionResult(
            source_file=document.filename or str(document.path),
            source_path=document.path,
            components=components,
            connections=connections,
            fault_codes=fault_codes,
            tables=tables,
            metadata=metadata,
        )

"""
Extraction Routes - PDF extraction endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

router = APIRouter()


class ExtractionResponse(BaseModel):
    """Extraction result response."""

    filename: str
    component_count: int
    fault_code_count: int
    table_count: int
    quality_score: float | None


@router.post("/extract", response_model=ExtractionResponse)
async def extract_pdf(file: UploadFile = File(...)):
    """
    Extract structured data from a PDF document.

    Upload a PDF file and receive extracted:
    - Fault codes
    - Components
    - Wiring connections
    - Tables
    """
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # TODO: Integrate with extraction domain
    return ExtractionResponse(
        filename=file.filename,
        component_count=0,
        fault_code_count=0,
        table_count=0,
        quality_score=None,
    )


@router.get("/status/{job_id}")
async def get_extraction_status(job_id: str):
    """Get status of an extraction job."""
    # TODO: Implement job tracking
    return {
        "job_id": job_id,
        "status": "unknown",
    }

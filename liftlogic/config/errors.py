"""
Error Taxonomy - Consistent error codes across the application.

Usage:
    from liftlogic.config.errors import ErrorCode, LiftLogicError

    raise LiftLogicError(ErrorCode.EXTRACTION_FAILED, "PDF parsing failed")
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Standardized error codes for machine-readable error responses."""

    # Extraction errors
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    EXTRACTION_TIMEOUT = "EXTRACTION_TIMEOUT"
    EXTRACTION_INVALID_PDF = "EXTRACTION_INVALID_PDF"
    EXTRACTION_QUALITY_LOW = "EXTRACTION_QUALITY_LOW"

    # Search errors
    SEARCH_INVALID_QUERY = "SEARCH_INVALID_QUERY"
    SEARCH_INDEX_UNAVAILABLE = "SEARCH_INDEX_UNAVAILABLE"
    SEARCH_NO_RESULTS = "SEARCH_NO_RESULTS"

    # Knowledge graph errors
    KNOWLEDGE_NODE_NOT_FOUND = "KNOWLEDGE_NODE_NOT_FOUND"
    KNOWLEDGE_GRAPH_UNAVAILABLE = "KNOWLEDGE_GRAPH_UNAVAILABLE"
    KNOWLEDGE_INVALID_EDGE = "KNOWLEDGE_INVALID_EDGE"

    # Diagnosis errors
    DIAGNOSIS_FAILED = "DIAGNOSIS_FAILED"
    DIAGNOSIS_INVALID_CODE = "DIAGNOSIS_INVALID_CODE"
    DIAGNOSIS_NO_CONTEXT = "DIAGNOSIS_NO_CONTEXT"

    # LLM/Model errors
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
    LLM_INVALID_RESPONSE = "LLM_INVALID_RESPONSE"
    LLM_AUTH_FAILED = "LLM_AUTH_FAILED"

    # Storage errors
    STORAGE_CONNECTION_FAILED = "STORAGE_CONNECTION_FAILED"
    STORAGE_READ_FAILED = "STORAGE_READ_FAILED"
    STORAGE_WRITE_FAILED = "STORAGE_WRITE_FAILED"

    # Security errors
    SECURITY_UNAUTHORIZED = "SECURITY_UNAUTHORIZED"
    SECURITY_FORBIDDEN = "SECURITY_FORBIDDEN"
    SECURITY_RATE_LIMITED = "SECURITY_RATE_LIMITED"

    # General errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"


class LiftLogicError(Exception):
    """Base exception with error code support."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code.value}] {message}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to API-friendly dictionary."""
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }


# Domain-specific exceptions for cleaner imports
class ExtractionError(LiftLogicError):
    """Extraction domain errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.EXTRACTION_FAILED, message, details)


class SearchError(LiftLogicError):
    """Search domain errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.SEARCH_INVALID_QUERY, message, details)


class DiagnosisError(LiftLogicError):
    """Diagnosis domain errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.DIAGNOSIS_FAILED, message, details)


class LLMError(LiftLogicError):
    """LLM/model errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.LLM_UNAVAILABLE, message, details)


class StorageError(LiftLogicError):
    """Storage/database errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.STORAGE_CONNECTION_FAILED, message, details)

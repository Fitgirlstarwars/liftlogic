"""
Configuration - Application settings, error taxonomy, and artifact manifests.
"""

from .errors import (
    DiagnosisError,
    ErrorCode,
    ExtractionError,
    LiftLogicError,
    LLMError,
    SearchError,
    StorageError,
)
from .manifest import (
    ArtifactManifest,
    ManifestItem,
    compute_file_checksum,
    create_faiss_manifest,
    create_graph_manifest,
)
from .settings import Settings, get_settings

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    # Errors
    "ErrorCode",
    "LiftLogicError",
    "ExtractionError",
    "SearchError",
    "DiagnosisError",
    "LLMError",
    "StorageError",
    # Manifests
    "ArtifactManifest",
    "ManifestItem",
    "compute_file_checksum",
    "create_faiss_manifest",
    "create_graph_manifest",
]

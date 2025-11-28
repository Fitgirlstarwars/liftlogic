"""
Configuration - Application settings, error taxonomy, and artifact manifests.
"""

from .settings import Settings, get_settings
from .errors import (
    ErrorCode,
    LiftLogicError,
    ExtractionError,
    SearchError,
    DiagnosisError,
    LLMError,
    StorageError,
)
from .manifest import (
    ArtifactManifest,
    ManifestItem,
    compute_file_checksum,
    create_faiss_manifest,
    create_graph_manifest,
)

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

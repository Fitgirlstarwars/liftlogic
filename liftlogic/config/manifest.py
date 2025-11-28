"""
Artifact Manifest - Track build artifacts for reproducibility.

Manifests are created for:
- FAISS indices (model, dimension, document count)
- Graph exports (node count, edge count)
- Cache files (TTL, entry count)

Usage:
    from liftlogic.config.manifest import ArtifactManifest, ManifestItem

    manifest = ArtifactManifest(
        artifact_type="faiss_index",
        model="all-MiniLM-L6-v2",
        dim=384,
    )
    manifest.add_item("/path/to/index.faiss", checksum="abc123")
    manifest.save("/path/to/manifest.json")
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ManifestItem:
    """Single item in the manifest."""

    path: str
    checksum: str
    bytes: int | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class ArtifactManifest:
    """
    Manifest for build artifacts (indices, exports, caches).

    Provides:
    - Model/version/dimension tracking
    - Checksum verification
    - Source/provenance tracking
    - Timestamps for debugging
    """

    artifact_type: str  # "faiss_index", "graph_export", "cache", "extraction"
    model: str  # e.g., "all-MiniLM-L6-v2", "gemini-2.0-flash"
    dim: int | None = None  # Vector dimension
    source: str | None = None  # Source dataset or commit hash
    schema_version: str = "1.0.0"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    items: list[ManifestItem] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_item(
        self,
        path: str | Path,
        checksum: str | None = None,
        compute_checksum: bool = True,
    ) -> ManifestItem:
        """
        Add an item to the manifest.

        Args:
            path: Path to the artifact file
            checksum: Pre-computed checksum (optional)
            compute_checksum: Compute SHA256 if checksum not provided

        Returns:
            The created ManifestItem
        """
        path = Path(path)

        if checksum is None and compute_checksum and path.exists():
            checksum = compute_file_checksum(path)

        item = ManifestItem(
            path=str(path),
            checksum=checksum or "",
            bytes=path.stat().st_size if path.exists() else None,
        )
        self.items.append(item)
        return item

    def validate(self) -> list[str]:
        """
        Validate the manifest.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self.artifact_type:
            errors.append("artifact_type is required")

        if not self.model:
            errors.append("model is required")

        if not self.items:
            errors.append("at least one manifest item is required")

        for i, item in enumerate(self.items):
            if not item.path:
                errors.append(f"item[{i}]: path is required")
            if not item.checksum:
                errors.append(f"item[{i}]: checksum is required")

        return errors

    def verify(self) -> list[str]:
        """
        Verify all items exist and checksums match.

        Returns:
            List of verification errors (empty if all valid)
        """
        errors = []

        for item in self.items:
            path = Path(item.path)

            if not path.exists():
                errors.append(f"File not found: {item.path}")
                continue

            if item.checksum:
                actual = compute_file_checksum(path)
                if actual != item.checksum:
                    errors.append(
                        f"Checksum mismatch for {item.path}: "
                        f"expected {item.checksum[:16]}..., got {actual[:16]}..."
                    )

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "artifact_type": self.artifact_type,
            "model": self.model,
            "dim": self.dim,
            "source": self.source,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "items": [
                {
                    "path": item.path,
                    "checksum": item.checksum,
                    "bytes": item.bytes,
                    "created_at": item.created_at,
                }
                for item in self.items
            ],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArtifactManifest:
        """Create manifest from dictionary."""
        items = [
            ManifestItem(
                path=item["path"],
                checksum=item["checksum"],
                bytes=item.get("bytes"),
                created_at=item.get("created_at", ""),
            )
            for item in data.get("items", [])
        ]

        return cls(
            artifact_type=data["artifact_type"],
            model=data["model"],
            dim=data.get("dim"),
            source=data.get("source"),
            schema_version=data.get("schema_version", "1.0.0"),
            created_at=data.get("created_at", ""),
            items=items,
            metadata=data.get("metadata", {}),
        )

    def save(self, path: str | Path) -> None:
        """Save manifest to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str | Path) -> ArtifactManifest:
        """Load manifest from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)


def compute_file_checksum(path: Path, algorithm: str = "sha256") -> str:
    """
    Compute checksum of a file.

    Args:
        path: Path to file
        algorithm: Hash algorithm (default: sha256)

    Returns:
        Hex digest of the file
    """
    hasher = hashlib.new(algorithm)

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


# Convenience functions for common artifact types
def create_faiss_manifest(
    index_path: Path,
    model: str,
    dim: int,
    doc_count: int,
    source: str | None = None,
) -> ArtifactManifest:
    """Create manifest for FAISS index."""
    manifest = ArtifactManifest(
        artifact_type="faiss_index",
        model=model,
        dim=dim,
        source=source,
        metadata={"document_count": doc_count},
    )
    manifest.add_item(index_path)
    return manifest


def create_graph_manifest(
    graph_path: Path,
    node_count: int,
    edge_count: int,
    source: str | None = None,
) -> ArtifactManifest:
    """Create manifest for graph export."""
    manifest = ArtifactManifest(
        artifact_type="graph_export",
        model="networkx",
        source=source,
        metadata={
            "node_count": node_count,
            "edge_count": edge_count,
        },
    )
    manifest.add_item(graph_path)
    return manifest

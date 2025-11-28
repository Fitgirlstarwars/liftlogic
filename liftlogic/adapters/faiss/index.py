"""
FAISS Index - Vector similarity search.

Features:
- Async-compatible operations
- Index persistence
- Batch operations
- Metadata storage alongside vectors
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import faiss
import numpy as np

logger = logging.getLogger(__name__)

__all__ = ["FAISSIndex"]


class FAISSIndex:
    """
    FAISS vector index for semantic search.

    Example:
        >>> index = FAISSIndex(dimension=384)
        >>> await index.add_vectors(embeddings, metadata_list)
        >>> results = await index.search(query_embedding, k=10)
    """

    def __init__(
        self,
        dimension: int = 384,
        index_type: str = "IVFFlat",
        nlist: int = 100,
    ) -> None:
        """
        Initialize FAISS index.

        Args:
            dimension: Vector dimension (384 for MiniLM, 768 for MPNet)
            index_type: Index type ("Flat", "IVFFlat", "HNSW")
            nlist: Number of clusters for IVF index
        """
        self.dimension = dimension
        self.index_type = index_type
        self.nlist = nlist

        self._index: faiss.Index | None = None
        self._metadata: list[dict[str, Any]] = []
        self._is_trained = False

    def _create_index(self) -> faiss.Index:
        """Create FAISS index based on type."""
        if self.index_type == "Flat":
            return faiss.IndexFlatIP(self.dimension)
        elif self.index_type == "IVFFlat":
            quantizer = faiss.IndexFlatIP(self.dimension)
            index = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist)
            return index
        elif self.index_type == "HNSW":
            return faiss.IndexHNSWFlat(self.dimension, 32)
        else:
            return faiss.IndexFlatIP(self.dimension)

    async def initialize(self) -> None:
        """Initialize empty index."""
        self._index = self._create_index()
        self._metadata = []
        logger.info(
            "FAISS index initialized: dimension=%d, type=%s",
            self.dimension,
            self.index_type,
        )

    async def add_vectors(
        self,
        vectors: np.ndarray,
        metadata: list[dict[str, Any]],
    ) -> None:
        """
        Add vectors with metadata.

        Args:
            vectors: numpy array of shape (n, dimension)
            metadata: List of metadata dicts (same length as vectors)
        """
        if self._index is None:
            await self.initialize()
        assert self._index is not None  # Guaranteed by initialize()

        vectors = np.ascontiguousarray(vectors.astype("float32"))

        # Normalize for inner product (cosine similarity)
        faiss.normalize_L2(vectors)

        # Train IVF index if needed
        if self.index_type == "IVFFlat" and not self._is_trained:
            if len(vectors) >= self.nlist:
                await asyncio.to_thread(self._index.train, vectors)
                self._is_trained = True

        # Add vectors
        await asyncio.to_thread(self._index.add, vectors)
        self._metadata.extend(metadata)

        logger.debug("Added %d vectors to index", len(vectors))

    async def search(
        self,
        query_vector: np.ndarray,
        k: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query vector of shape (dimension,) or (1, dimension)
            k: Number of results

        Returns:
            List of dicts with 'score', 'metadata', and 'index'
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        # Reshape if needed
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        query_vector = np.ascontiguousarray(query_vector.astype("float32"))
        faiss.normalize_L2(query_vector)

        # Search
        scores, indices = await asyncio.to_thread(
            self._index.search, query_vector, min(k, self._index.ntotal)
        )

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self._metadata):
                results.append(
                    {
                        "score": float(score),
                        "index": int(idx),
                        "metadata": self._metadata[idx],
                    }
                )

        return results

    async def save(self, path: str | Path) -> None:
        """
        Save index to disk.

        Args:
            path: Directory to save index
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        index_path = path / "faiss_index.bin"
        await asyncio.to_thread(faiss.write_index, self._index, str(index_path))

        # Save metadata (use to_thread to avoid blocking)
        metadata_path = path / "metadata.json"
        metadata = {
            "dimension": self.dimension,
            "index_type": self.index_type,
            "nlist": self.nlist,
            "is_trained": self._is_trained,
            "metadata": self._metadata,
        }
        await asyncio.to_thread(self._write_json, metadata_path, metadata)

        ntotal = self._index.ntotal if self._index else 0
        logger.info("Index saved to %s (%d vectors)", path, ntotal)

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        """Write JSON file (sync helper for to_thread)."""
        with open(path, "w") as f:
            json.dump(data, f)

    async def load(self, path: str | Path) -> None:
        """
        Load index from disk.

        Args:
            path: Directory containing saved index
        """
        path = Path(path)

        # Load FAISS index
        index_path = path / "faiss_index.bin"
        self._index = await asyncio.to_thread(faiss.read_index, str(index_path))

        # Load metadata (use to_thread to avoid blocking)
        metadata_path = path / "metadata.json"
        data = await asyncio.to_thread(self._read_json, metadata_path)
        self.dimension = data["dimension"]
        self.index_type = data["index_type"]
        self.nlist = data["nlist"]
        self._is_trained = data["is_trained"]
        self._metadata = data["metadata"]

        ntotal = self._index.ntotal if self._index else 0
        logger.info("Index loaded from %s (%d vectors)", path, ntotal)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        """Read JSON file (sync helper for to_thread)."""
        with open(path) as f:
            result: dict[str, Any] = json.load(f)
            return result

    @property
    def size(self) -> int:
        """Get number of vectors in index."""
        return self._index.ntotal if self._index else 0

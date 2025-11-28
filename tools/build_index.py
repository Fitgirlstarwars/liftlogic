#!/usr/bin/env python3
"""
Build Index - Load imported data into SQLite and FAISS.

This script:
1. Loads platinum JSONs into SQLite with FTS5
2. Creates sentence embeddings
3. Builds FAISS vector index
4. Loads graph data into knowledge store

Usage:
    python tools/build_index.py
    python tools/build_index.py --skip-embeddings  # Fast mode, skip FAISS
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from liftlogic.adapters.sqlite import SQLiteRepository
from liftlogic.adapters.faiss import FAISSIndex
from liftlogic.config import get_settings, create_faiss_manifest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PLATINUM_DIR = DATA_DIR / "processed" / "platinum"
GRAPH_FILE = DATA_DIR / "graph" / "graph_production.jsonl"


async def load_platinum_to_sqlite(repo: SQLiteRepository) -> int:
    """Load platinum JSONs into SQLite."""
    logger.info("Loading platinum JSONs into SQLite...")

    count = 0
    fault_count = 0

    for json_file in sorted(PLATINUM_DIR.glob("*.json")):
        try:
            with open(json_file) as f:
                data = json.load(f)

            metadata = data.get("metadata", {})
            doc_props = metadata.get("document_properties", {})

            # Insert document
            doc_id = await repo.insert_document(
                filename=metadata.get("filename", json_file.name),
                content=data.get("full_text", "")[:50000],  # Limit content size
                manufacturer=doc_props.get("manufacturer"),
                model=doc_props.get("model"),
                document_type=doc_props.get("document_type"),
                filepath=str(json_file),
                metadata=metadata,
            )

            count += 1

            # Extract and insert fault codes from structured content
            structured = data.get("structured_content", {})
            for page in structured.get("pages", []):
                for table in page.get("tables", []):
                    # Look for fault code tables
                    headers = [h.lower() for h in table.get("headers", [])]
                    if any("fault" in h or "code" in h or "error" in h for h in headers):
                        for row in table.get("rows", []):
                            if row and len(row) >= 2:
                                code = str(row[0]).strip()
                                desc = str(row[1]).strip() if len(row) > 1 else ""
                                if code and len(code) < 20:  # Reasonable code length
                                    await repo.insert_fault_code(
                                        code=code,
                                        description=desc,
                                        manufacturer=doc_props.get("manufacturer"),
                                        document_id=doc_id,
                                    )
                                    fault_count += 1

            if count % 100 == 0:
                logger.info("  Processed %d documents...", count)

        except Exception as e:
            logger.warning("Failed to process %s: %s", json_file.name, e)

    logger.info("Loaded %d documents, %d fault codes", count, fault_count)
    return count


async def build_faiss_index(repo: SQLiteRepository, index: FAISSIndex) -> int:
    """Build FAISS index from documents."""
    logger.info("Building FAISS index (this may take a few minutes)...")

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
        return 0

    settings = get_settings()
    model = SentenceTransformer(settings.embedding_model)

    # Get all documents
    conn = await repo._get_connection()
    cursor = await conn.execute(
        "SELECT id, filename, manufacturer, content FROM documents WHERE content IS NOT NULL"
    )
    rows = await cursor.fetchall()

    if not rows:
        logger.warning("No documents found in database")
        return 0

    logger.info("Generating embeddings for %d documents...", len(rows))

    # Process in batches
    batch_size = 32
    all_embeddings = []
    all_metadata = []

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]

        texts = []
        metadata = []
        for row in batch:
            # Use first 1000 chars for embedding
            text = (row["content"] or "")[:1000]
            texts.append(text)
            metadata.append({
                "doc_id": row["id"],
                "filename": row["filename"],
                "manufacturer": row["manufacturer"],
            })

        # Generate embeddings
        embeddings = model.encode(texts, show_progress_bar=False)
        all_embeddings.append(embeddings)
        all_metadata.extend(metadata)

        if (i + batch_size) % 500 == 0:
            logger.info("  Embedded %d/%d documents...", min(i + batch_size, len(rows)), len(rows))

    # Combine and add to index
    embeddings_array = np.vstack(all_embeddings)
    await index.add_vectors(embeddings_array, all_metadata)

    # Save index
    index_path = DATA_DIR / "indices" / "faiss"
    await index.save(index_path)

    # Create manifest
    manifest = create_faiss_manifest(
        index_path=index_path / "faiss_index.bin",
        model=settings.embedding_model,
        dim=settings.embedding_dimension,
        doc_count=len(all_metadata),
        source="platinum_jsons",
    )
    manifest.save(index_path / "manifest.json")

    logger.info("FAISS index built with %d vectors", len(all_metadata))
    return len(all_metadata)


async def load_graph_data() -> tuple[int, int]:
    """Load graph data from JSONL."""
    logger.info("Loading graph data...")

    if not GRAPH_FILE.exists():
        logger.warning("Graph file not found: %s", GRAPH_FILE)
        return 0, 0

    nodes = []
    edges = []

    with open(GRAPH_FILE) as f:
        for line in f:
            data = json.loads(line.strip())
            if data.get("entity") == "node":
                nodes.append(data)
            elif data.get("entity") == "edge":
                edges.append(data)

    # Save as structured JSON for the knowledge domain
    graph_dir = DATA_DIR / "graph"
    with open(graph_dir / "nodes.json", "w") as f:
        json.dump(nodes, f)
    with open(graph_dir / "edges.json", "w") as f:
        json.dump(edges, f)

    logger.info("Loaded %d nodes, %d edges", len(nodes), len(edges))
    return len(nodes), len(edges)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Build search indices from imported data")
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip FAISS index building")
    args = parser.parse_args()

    settings = get_settings()

    # Initialize SQLite
    repo = SQLiteRepository(settings.db_path)
    await repo.initialize()

    # Check if already loaded
    doc_count = await repo.get_document_count()
    if doc_count > 0:
        logger.info("Database already has %d documents. Skipping SQLite load.", doc_count)
    else:
        # Load documents
        doc_count = await load_platinum_to_sqlite(repo)

    # Build FAISS index
    vector_count = 0
    if not args.skip_embeddings:
        index = FAISSIndex(
            dimension=settings.embedding_dimension,
            index_type="Flat",  # Use Flat for small datasets
        )
        await index.initialize()

        index_path = DATA_DIR / "indices" / "faiss" / "faiss_index.bin"
        if index_path.exists():
            logger.info("FAISS index already exists. Loading...")
            await index.load(index_path.parent)
            vector_count = index.size
        else:
            vector_count = await build_faiss_index(repo, index)

    # Load graph
    node_count, edge_count = await load_graph_data()

    # Summary
    print("\n" + "=" * 50)
    print("INDEX BUILD COMPLETE")
    print("=" * 50)
    print(f"Documents in SQLite:  {doc_count:,}")
    print(f"Vectors in FAISS:     {vector_count:,}")
    print(f"Graph nodes:          {node_count:,}")
    print(f"Graph edges:          {edge_count:,}")
    print("=" * 50)

    await repo.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

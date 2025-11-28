#!/usr/bin/env python3
"""
Data Import Tool - Import pre-processed data from other LiftLogic builds.

This script imports:
1. Platinum JSONs (2,307 high-quality extractions)
2. Graph data (fault codes, components, procedures)

Usage:
    python tools/import_data.py --source /Users/fender/Desktop/data
    python tools/import_data.py --graph-only /path/to/graph_production.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def import_platinum_jsons(source_dir: Path) -> int:
    """
    Import platinum JSONs from external source.

    Args:
        source_dir: Path to processed/ingested_json/platinum/

    Returns:
        Number of files imported
    """
    platinum_src = source_dir / "processed" / "ingested_json" / "platinum"

    if not platinum_src.exists():
        logger.error("Platinum source not found: %s", platinum_src)
        return 0

    # Create destination
    dest = DATA_DIR / "processed" / "platinum"
    dest.mkdir(parents=True, exist_ok=True)

    count = 0
    for json_file in platinum_src.glob("*.json"):
        dest_file = dest / json_file.name
        if not dest_file.exists():
            shutil.copy2(json_file, dest_file)
            count += 1

    logger.info("Imported %d platinum JSONs to %s", count, dest)
    return count


def import_graph_data(graph_file: Path) -> dict[str, int]:
    """
    Import graph JSONL data.

    Args:
        graph_file: Path to graph_production.jsonl

    Returns:
        Stats dict with node/edge counts
    """
    if not graph_file.exists():
        logger.error("Graph file not found: %s", graph_file)
        return {"nodes": 0, "edges": 0}

    # Create destination
    dest = DATA_DIR / "graph"
    dest.mkdir(parents=True, exist_ok=True)

    # Copy graph file
    dest_file = dest / "graph_production.jsonl"
    shutil.copy2(graph_file, dest_file)

    # Count entities
    nodes = 0
    edges = 0

    with open(dest_file) as f:
        for line in f:
            data = json.loads(line.strip())
            if data.get("entity") == "node":
                nodes += 1
            elif data.get("entity") == "edge":
                edges += 1

    logger.info("Imported graph: %d nodes, %d edges", nodes, edges)

    # Create manifest
    manifest = {
        "source_file": str(graph_file),
        "destination": str(dest_file),
        "nodes": nodes,
        "edges": edges,
        "format": "jsonl",
    }

    manifest_file = dest / "manifest.json"
    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2)

    return {"nodes": nodes, "edges": edges}


def create_data_index(data_dir: Path) -> dict[str, Any]:
    """
    Create an index of all imported data.

    Returns:
        Index dict with file counts by category
    """
    index: dict[str, Any] = {
        "platinum_jsons": 0,
        "graph_nodes": 0,
        "graph_edges": 0,
        "manufacturers": set(),
        "document_types": set(),
    }

    # Count platinum JSONs
    platinum_dir = data_dir / "processed" / "platinum"
    if platinum_dir.exists():
        for json_file in platinum_dir.glob("*.json"):
            index["platinum_jsons"] += 1

            try:
                with open(json_file) as f:
                    data = json.load(f)

                meta = data.get("metadata", {})
                doc_props = meta.get("document_properties", {})

                if manufacturer := doc_props.get("manufacturer"):
                    index["manufacturers"].add(manufacturer)
                if doc_type := doc_props.get("document_type"):
                    index["document_types"].add(doc_type)

            except (json.JSONDecodeError, KeyError):
                continue

    # Count graph data
    graph_manifest = data_dir / "graph" / "manifest.json"
    if graph_manifest.exists():
        with open(graph_manifest) as f:
            manifest = json.load(f)
            index["graph_nodes"] = manifest.get("nodes", 0)
            index["graph_edges"] = manifest.get("edges", 0)

    # Convert sets to lists for JSON serialization
    index["manufacturers"] = sorted(index["manufacturers"])
    index["document_types"] = sorted(index["document_types"])

    # Save index
    index_file = data_dir / "index.json"
    with open(index_file, "w") as f:
        json.dump(index, f, indent=2)

    return index


def main() -> int:
    parser = argparse.ArgumentParser(description="Import pre-processed LiftLogic data")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("/Users/fender/Desktop/data"),
        help="Source data directory (default: /Users/fender/Desktop/data)",
    )
    parser.add_argument(
        "--graph-only",
        type=Path,
        help="Import only graph JSONL file",
    )
    parser.add_argument(
        "--platinum-only",
        action="store_true",
        help="Import only platinum JSONs",
    )

    args = parser.parse_args()

    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    total_imported = 0

    if args.graph_only:
        # Import graph only
        stats = import_graph_data(args.graph_only)
        total_imported = stats["nodes"] + stats["edges"]

    elif args.platinum_only:
        # Import platinum only
        total_imported = import_platinum_jsons(args.source)

    else:
        # Import everything
        logger.info("Importing from: %s", args.source)

        # Import platinum JSONs
        platinum_count = import_platinum_jsons(args.source)
        total_imported += platinum_count

        # Import graph data (check both locations)
        graph_paths = [
            args.source / "graph_production.jsonl",
            Path("/Users/fender/Desktop/liftlogic-new-gemini/data/graph_production.jsonl"),
        ]

        for graph_path in graph_paths:
            if graph_path.exists():
                stats = import_graph_data(graph_path)
                total_imported += stats["nodes"] + stats["edges"]
                break

    # Create index
    index = create_data_index(DATA_DIR)

    # Summary
    print("\n" + "=" * 50)
    print("IMPORT SUMMARY")
    print("=" * 50)
    print(f"Platinum JSONs:  {index['platinum_jsons']:,}")
    print(f"Graph Nodes:     {index['graph_nodes']:,}")
    print(f"Graph Edges:     {index['graph_edges']:,}")
    print(f"Manufacturers:   {', '.join(index['manufacturers'][:5])}{'...' if len(index['manufacturers']) > 5 else ''}")
    print(f"Document Types:  {len(index['document_types'])}")
    print("=" * 50)

    return 0 if total_imported > 0 else 1


if __name__ == "__main__":
    sys.exit(main())

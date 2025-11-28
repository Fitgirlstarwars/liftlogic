#!/usr/bin/env python3
"""
EVIH to LiftLogic Migration Script

Migrates data from the old EVIH project structure to the new LiftLogic format.

Usage:
    python migrate_from_evih.py --source /path/to/evih --dest /path/to/liftlogic/data

This script:
1. Migrates SQLite database schema and data
2. Converts FAISS indexes to new format
3. Migrates documents and extractions
4. Updates file references
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def migrate_database(source_db: Path, dest_db: Path) -> int:
    """
    Migrate SQLite database from EVIH to LiftLogic schema.

    Args:
        source_db: Path to source database
        dest_db: Path to destination database

    Returns:
        Number of records migrated
    """
    if not source_db.exists():
        logger.warning("Source database not found: %s", source_db)
        return 0

    logger.info("Migrating database from %s", source_db)

    # Connect to source
    src_conn = sqlite3.connect(source_db)
    src_conn.row_factory = sqlite3.Row

    # Create destination
    dest_db.parent.mkdir(parents=True, exist_ok=True)
    dest_conn = sqlite3.connect(dest_db)

    # Create new schema
    dest_conn.executescript("""
        -- Documents table
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            file_path TEXT,
            file_hash TEXT,
            manufacturer TEXT,
            model TEXT,
            doc_type TEXT,
            page_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Chunks table (for RAG)
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER REFERENCES documents(id),
            content TEXT NOT NULL,
            page_number INTEGER,
            chunk_index INTEGER,
            embedding_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Components table
        CREATE TABLE IF NOT EXISTS components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER REFERENCES documents(id),
            component_id TEXT,
            name TEXT NOT NULL,
            component_type TEXT,
            specs JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Fault codes table
        CREATE TABLE IF NOT EXISTS fault_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER REFERENCES documents(id),
            code TEXT NOT NULL,
            description TEXT,
            severity TEXT,
            causes JSON,
            remedies JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Connections table
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER REFERENCES documents(id),
            source_component TEXT,
            target_component TEXT,
            connection_type TEXT,
            label TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Create FTS5 virtual table
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            content,
            content='chunks',
            content_rowid='id'
        );

        -- Triggers for FTS sync
        CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, content) VALUES (new.id, new.content);
        END;

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
        CREATE INDEX IF NOT EXISTS idx_components_document ON components(document_id);
        CREATE INDEX IF NOT EXISTS idx_fault_codes_code ON fault_codes(code);
    """)

    records_migrated = 0

    # Migrate documents
    try:
        # Try different possible table names from old schema
        for table_name in ["documents", "pdf_documents", "manuals"]:
            try:
                rows = src_conn.execute(f"SELECT * FROM {table_name}").fetchall()
                if rows:
                    logger.info("Found %d documents in %s", len(rows), table_name)
                    for row in rows:
                        dest_conn.execute("""
                            INSERT INTO documents (title, file_path, manufacturer, doc_type, created_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            row.get("title") or row.get("name") or "Unknown",
                            row.get("file_path") or row.get("path"),
                            row.get("manufacturer"),
                            row.get("doc_type") or row.get("type"),
                            row.get("created_at") or datetime.now().isoformat(),
                        ))
                        records_migrated += 1
                    break
            except sqlite3.OperationalError:
                continue
    except Exception as e:
        logger.warning("Could not migrate documents: %s", e)

    # Migrate chunks/embeddings
    try:
        for table_name in ["chunks", "text_chunks", "embeddings"]:
            try:
                rows = src_conn.execute(f"SELECT * FROM {table_name}").fetchall()
                if rows:
                    logger.info("Found %d chunks in %s", len(rows), table_name)
                    for row in rows:
                        dest_conn.execute("""
                            INSERT INTO chunks (document_id, content, page_number, chunk_index)
                            VALUES (?, ?, ?, ?)
                        """, (
                            row.get("document_id") or row.get("doc_id") or 1,
                            row.get("content") or row.get("text") or "",
                            row.get("page_number") or row.get("page"),
                            row.get("chunk_index") or row.get("index") or 0,
                        ))
                        records_migrated += 1
                    break
            except sqlite3.OperationalError:
                continue
    except Exception as e:
        logger.warning("Could not migrate chunks: %s", e)

    dest_conn.commit()
    src_conn.close()
    dest_conn.close()

    logger.info("Migrated %d total records", records_migrated)
    return records_migrated


def migrate_faiss_index(source_dir: Path, dest_dir: Path) -> bool:
    """
    Migrate FAISS index files.

    Args:
        source_dir: Source directory containing FAISS index
        dest_dir: Destination directory

    Returns:
        True if successful
    """
    faiss_files = list(source_dir.glob("*.faiss")) + list(source_dir.glob("*.index"))

    if not faiss_files:
        logger.info("No FAISS index files found in %s", source_dir)
        return False

    dest_dir.mkdir(parents=True, exist_ok=True)

    for faiss_file in faiss_files:
        dest_path = dest_dir / faiss_file.name
        logger.info("Copying FAISS index: %s -> %s", faiss_file, dest_path)
        shutil.copy2(faiss_file, dest_path)

    return True


def migrate_documents(source_dir: Path, dest_dir: Path) -> int:
    """
    Migrate PDF documents and extractions.

    Args:
        source_dir: Source documents directory
        dest_dir: Destination documents directory

    Returns:
        Number of files migrated
    """
    if not source_dir.exists():
        logger.warning("Source documents directory not found: %s", source_dir)
        return 0

    dest_dir.mkdir(parents=True, exist_ok=True)
    files_migrated = 0

    # Copy PDFs
    for pdf_file in source_dir.rglob("*.pdf"):
        dest_path = dest_dir / pdf_file.name
        if not dest_path.exists():
            logger.info("Copying PDF: %s", pdf_file.name)
            shutil.copy2(pdf_file, dest_path)
            files_migrated += 1

    # Copy JSON extractions
    for json_file in source_dir.rglob("*.json"):
        dest_path = dest_dir / "extractions" / json_file.name
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if not dest_path.exists():
            logger.info("Copying extraction: %s", json_file.name)
            shutil.copy2(json_file, dest_path)
            files_migrated += 1

    logger.info("Migrated %d document files", files_migrated)
    return files_migrated


def create_symlink(source: Path, dest: Path) -> bool:
    """
    Create symlink from dest to source (for data directory).

    Args:
        source: Source path (existing data)
        dest: Destination symlink path

    Returns:
        True if successful
    """
    if dest.exists():
        if dest.is_symlink():
            dest.unlink()
        else:
            logger.warning("Destination exists and is not a symlink: %s", dest)
            return False

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.symlink_to(source)
        logger.info("Created symlink: %s -> %s", dest, source)
        return True
    except Exception as e:
        logger.error("Failed to create symlink: %s", e)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Migrate data from EVIH to LiftLogic"
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to source EVIH project",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        required=True,
        help="Path to destination LiftLogic data directory",
    )
    parser.add_argument(
        "--symlink",
        action="store_true",
        help="Create symlink instead of copying data",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )

    args = parser.parse_args()

    logger.info("Starting migration from %s to %s", args.source, args.dest)

    if args.dry_run:
        logger.info("DRY RUN - no changes will be made")

    # Find source paths
    source_data = args.source / "data"
    if not source_data.exists():
        # Try alternative locations
        for alt in ["uploads", "documents", "pdfs"]:
            alt_path = args.source / alt
            if alt_path.exists():
                source_data = alt_path
                break

    # Find database
    source_db = None
    for db_name in ["liftlogic.db", "evih.db", "database.db", "app.db"]:
        db_path = args.source / db_name
        if db_path.exists():
            source_db = db_path
            break
        # Check in data directory
        db_path = source_data / db_name
        if db_path.exists():
            source_db = db_path
            break

    if not args.dry_run:
        # Create destination structure
        args.dest.mkdir(parents=True, exist_ok=True)

        if args.symlink and source_data.exists():
            # Symlink data directory
            create_symlink(source_data, args.dest / "documents")
        else:
            # Copy documents
            migrate_documents(source_data, args.dest / "documents")

        # Migrate database
        if source_db:
            migrate_database(source_db, args.dest / "liftlogic.db")
        else:
            logger.warning("No source database found")

        # Migrate FAISS index
        for index_dir in [source_data, args.source / "indexes", args.source / "faiss"]:
            if migrate_faiss_index(index_dir, args.dest / "indexes"):
                break

    logger.info("Migration complete!")


if __name__ == "__main__":
    main()

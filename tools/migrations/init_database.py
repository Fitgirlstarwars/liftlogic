#!/usr/bin/env python3
"""
Initialize LiftLogic Database

Creates fresh database with proper schema for new installations.

Usage:
    python init_database.py --db /path/to/liftlogic.db
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

SCHEMA = """
-- ================================================================
-- LiftLogic Database Schema v2.0
-- ================================================================

-- Documents: Stores uploaded PDF documents
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    file_path TEXT,
    file_hash TEXT UNIQUE,
    manufacturer TEXT,
    model TEXT,
    doc_type TEXT,
    page_count INTEGER DEFAULT 0,
    extraction_status TEXT DEFAULT 'pending',
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chunks: Text chunks for RAG retrieval
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    page_number INTEGER,
    chunk_index INTEGER,
    embedding_id INTEGER,
    token_count INTEGER,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, page_number, chunk_index)
);

-- Components: Extracted electrical/mechanical components
CREATE TABLE IF NOT EXISTS components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    component_id TEXT NOT NULL,
    name TEXT NOT NULL,
    component_type TEXT,
    specs JSON,
    description TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, component_id)
);

-- Connections: Component relationships
CREATE TABLE IF NOT EXISTS connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    source_component TEXT NOT NULL,
    target_component TEXT NOT NULL,
    connection_type TEXT,
    label TEXT,
    wire_info JSON,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fault Codes: Error/fault code definitions
CREATE TABLE IF NOT EXISTS fault_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    description TEXT,
    severity TEXT,
    causes JSON,
    remedies JSON,
    related_components JSON,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Safety Items: Extracted safety warnings and procedures
CREATE TABLE IF NOT EXISTS safety_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT,
    severity TEXT,
    category TEXT,
    page_number INTEGER,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Query Cache: Cache for expensive LLM queries
CREATE TABLE IF NOT EXISTS query_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,
    query TEXT NOT NULL,
    response JSON NOT NULL,
    query_type TEXT,
    hit_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- User Sessions: Track user interactions
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    user_id TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- Query History: Log of queries for analytics
CREATE TABLE IF NOT EXISTS query_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    query TEXT NOT NULL,
    query_type TEXT,
    response_time_ms INTEGER,
    success BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================================================
-- Full-Text Search (FTS5)
-- ================================================================

-- FTS for chunk content
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content,
    content='chunks',
    content_rowid='id',
    tokenize='porter unicode61'
);

-- FTS for fault codes
CREATE VIRTUAL TABLE IF NOT EXISTS fault_codes_fts USING fts5(
    code,
    description,
    content='fault_codes',
    content_rowid='id',
    tokenize='porter unicode61'
);

-- ================================================================
-- Triggers
-- ================================================================

-- Sync chunks to FTS
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES('delete', old.id, old.content);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO chunks_fts(rowid, content) VALUES (new.id, new.content);
END;

-- Sync fault codes to FTS
CREATE TRIGGER IF NOT EXISTS fault_codes_ai AFTER INSERT ON fault_codes BEGIN
    INSERT INTO fault_codes_fts(rowid, code, description) VALUES (new.id, new.code, new.description);
END;

CREATE TRIGGER IF NOT EXISTS fault_codes_ad AFTER DELETE ON fault_codes BEGIN
    INSERT INTO fault_codes_fts(fault_codes_fts, rowid, code, description) VALUES('delete', old.id, old.code, old.description);
END;

-- Update document timestamp on modification
CREATE TRIGGER IF NOT EXISTS documents_update AFTER UPDATE ON documents BEGIN
    UPDATE documents SET updated_at = CURRENT_TIMESTAMP WHERE id = new.id;
END;

-- ================================================================
-- Indexes
-- ================================================================

CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_documents_manufacturer ON documents(manufacturer);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks(embedding_id);
CREATE INDEX IF NOT EXISTS idx_components_document ON components(document_id);
CREATE INDEX IF NOT EXISTS idx_components_type ON components(component_type);
CREATE INDEX IF NOT EXISTS idx_connections_source ON connections(source_component);
CREATE INDEX IF NOT EXISTS idx_connections_target ON connections(target_component);
CREATE INDEX IF NOT EXISTS idx_fault_codes_code ON fault_codes(code);
CREATE INDEX IF NOT EXISTS idx_fault_codes_severity ON fault_codes(severity);
CREATE INDEX IF NOT EXISTS idx_query_cache_key ON query_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_query_cache_expires ON query_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_query_history_session ON query_history(session_id);
CREATE INDEX IF NOT EXISTS idx_query_history_created ON query_history(created_at);
"""


def init_database(db_path: Path) -> None:
    """Initialize database with schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Initializing database at %s", db_path)

    conn = sqlite3.connect(db_path)

    try:
        conn.executescript(SCHEMA)
        conn.commit()
        logger.info("Database schema created successfully")

        # Verify tables
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        logger.info("Created tables: %s", ", ".join(tables))

    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Initialize LiftLogic database"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/liftlogic.db"),
        help="Path to database file",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing database",
    )

    args = parser.parse_args()

    if args.db.exists() and not args.force:
        logger.error("Database already exists. Use --force to overwrite.")
        return 1

    if args.db.exists() and args.force:
        logger.warning("Removing existing database")
        args.db.unlink()

    init_database(args.db)
    logger.info("Done!")
    return 0


if __name__ == "__main__":
    exit(main())

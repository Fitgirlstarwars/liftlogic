"""
SQLite Repository - Document storage with FTS5 search.

Features:
- Async operations via aiosqlite
- Full-text search with FTS5
- Document metadata storage
- Connection pooling
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

__all__ = ["SQLiteRepository"]


class SQLiteRepository:
    """
    SQLite repository for document storage.

    Example:
        >>> repo = SQLiteRepository("data/liftlogic.db")
        >>> await repo.initialize()
        >>> doc_id = await repo.insert_document({"title": "Manual", "content": "..."})
        >>> results = await repo.search_fts("fault code 505")
    """

    def __init__(self, db_path: str | Path) -> None:
        """
        Initialize repository.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: aiosqlite.Connection | None = None

    async def _get_connection(self) -> aiosqlite.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = await aiosqlite.connect(str(self.db_path))
            self._connection.row_factory = aiosqlite.Row
        return self._connection

    async def initialize(self) -> None:
        """Initialize database schema."""
        conn = await self._get_connection()

        await conn.executescript("""
            -- Documents table
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                filepath TEXT,
                manufacturer TEXT,
                model TEXT,
                document_type TEXT,
                content TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- FTS5 virtual table for full-text search
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                filename,
                manufacturer,
                model,
                content,
                content='documents',
                content_rowid='id',
                tokenize='porter'
            );

            -- Triggers to keep FTS in sync
            CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
                INSERT INTO documents_fts(rowid, filename, manufacturer, model, content)
                VALUES (new.id, new.filename, new.manufacturer, new.model, new.content);
            END;

            CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, filename, manufacturer, model, content)
                VALUES ('delete', old.id, old.filename, old.manufacturer, old.model, old.content);
            END;

            CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, filename, manufacturer, model, content)
                VALUES ('delete', old.id, old.filename, old.manufacturer, old.model, old.content);
                INSERT INTO documents_fts(rowid, filename, manufacturer, model, content)
                VALUES (new.id, new.filename, new.manufacturer, new.model, new.content);
            END;

            -- Fault codes table
            CREATE TABLE IF NOT EXISTS fault_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                manufacturer TEXT,
                description TEXT,
                severity TEXT,
                causes TEXT,
                remedies TEXT,
                document_id INTEGER,
                metadata TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            );

            -- Indexes
            CREATE INDEX IF NOT EXISTS idx_documents_manufacturer ON documents(manufacturer);
            CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
            CREATE INDEX IF NOT EXISTS idx_fault_codes_code ON fault_codes(code);
            CREATE INDEX IF NOT EXISTS idx_fault_codes_manufacturer ON fault_codes(manufacturer);
        """)

        await conn.commit()
        logger.info("Database initialized: %s", self.db_path)

    async def insert_document(
        self,
        filename: str,
        content: str,
        manufacturer: str | None = None,
        model: str | None = None,
        document_type: str | None = None,
        filepath: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Insert a document.

        Returns:
            Document ID
        """
        conn = await self._get_connection()

        cursor = await conn.execute(
            """
            INSERT INTO documents (filename, filepath, manufacturer, model, document_type, content, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                filepath,
                manufacturer,
                model,
                document_type,
                content,
                json.dumps(metadata) if metadata else None,
            ),
        )

        await conn.commit()
        return cursor.lastrowid

    async def get_document(self, doc_id: int) -> dict[str, Any] | None:
        """Get document by ID."""
        conn = await self._get_connection()

        cursor = await conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        )
        row = await cursor.fetchone()

        if row:
            return dict(row)
        return None

    async def search_fts(
        self,
        query: str,
        limit: int = 20,
        manufacturer: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Full-text search using FTS5.

        Args:
            query: Search query
            limit: Maximum results
            manufacturer: Optional manufacturer filter

        Returns:
            List of matching documents with BM25 scores
        """
        conn = await self._get_connection()

        # Build query with optional manufacturer filter
        if manufacturer:
            sql = """
                SELECT d.*, bm25(documents_fts) as score
                FROM documents_fts
                JOIN documents d ON documents_fts.rowid = d.id
                WHERE documents_fts MATCH ? AND d.manufacturer = ?
                ORDER BY score
                LIMIT ?
            """
            params = (query, manufacturer, limit)
        else:
            sql = """
                SELECT d.*, bm25(documents_fts) as score
                FROM documents_fts
                JOIN documents d ON documents_fts.rowid = d.id
                WHERE documents_fts MATCH ?
                ORDER BY score
                LIMIT ?
            """
            params = (query, limit)

        cursor = await conn.execute(sql, params)
        rows = await cursor.fetchall()

        return [dict(row) for row in rows]

    async def insert_fault_code(
        self,
        code: str,
        description: str,
        manufacturer: str | None = None,
        severity: str | None = None,
        causes: list[str] | None = None,
        remedies: list[str] | None = None,
        document_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Insert a fault code."""
        conn = await self._get_connection()

        cursor = await conn.execute(
            """
            INSERT INTO fault_codes
            (code, manufacturer, description, severity, causes, remedies, document_id, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code,
                manufacturer,
                description,
                severity,
                json.dumps(causes) if causes else None,
                json.dumps(remedies) if remedies else None,
                document_id,
                json.dumps(metadata) if metadata else None,
            ),
        )

        await conn.commit()
        return cursor.lastrowid

    async def get_fault_code(
        self,
        code: str,
        manufacturer: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get fault code(s) by code and optional manufacturer."""
        conn = await self._get_connection()

        if manufacturer:
            cursor = await conn.execute(
                "SELECT * FROM fault_codes WHERE code = ? AND manufacturer = ?",
                (code, manufacturer),
            )
        else:
            cursor = await conn.execute(
                "SELECT * FROM fault_codes WHERE code = ?", (code,)
            )

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_document_count(self) -> int:
        """Get total document count."""
        conn = await self._get_connection()
        cursor = await conn.execute("SELECT COUNT(*) FROM documents")
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

"""Tests for SQLite Repository."""

import pytest
from pathlib import Path
from .repository import SQLiteRepository


@pytest.fixture
async def repo(tmp_path: Path):
    """Create a test repository with temporary database."""
    db_path = tmp_path / "test.db"
    repo = SQLiteRepository(db_path)
    await repo.initialize()
    yield repo
    await repo.close()


async def test_initialize_creates_tables(repo: SQLiteRepository):
    """Test that initialize creates all required tables."""
    conn = await repo._get_connection()
    cursor = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    tables = {row[0] for row in await cursor.fetchall()}

    assert "documents" in tables
    assert "fault_codes" in tables
    assert "documents_fts" in tables


async def test_insert_and_get_document(repo: SQLiteRepository):
    """Test inserting and retrieving a document."""
    doc_id = await repo.insert_document(
        filename="test_manual.pdf",
        content="This is test content about elevator fault codes.",
        manufacturer="KONE",
        model="EcoSpace",
        document_type="manual",
    )

    assert doc_id is not None
    assert doc_id > 0

    doc = await repo.get_document(doc_id)
    assert doc is not None
    assert doc["filename"] == "test_manual.pdf"
    assert doc["manufacturer"] == "KONE"
    assert "elevator fault codes" in doc["content"]


async def test_search_fts(repo: SQLiteRepository):
    """Test full-text search."""
    # Insert test documents
    await repo.insert_document(
        filename="manual1.pdf",
        content="Fault code 505 indicates door zone sensor malfunction.",
        manufacturer="KONE",
    )
    await repo.insert_document(
        filename="manual2.pdf",
        content="Motor overload protection prevents damage.",
        manufacturer="Otis",
    )

    # Search for specific term
    results = await repo.search_fts("fault code 505")
    assert len(results) >= 1
    assert any("505" in r["content"] for r in results)

    # Search with manufacturer filter
    results = await repo.search_fts("motor", manufacturer="Otis")
    assert len(results) >= 1
    assert all(r["manufacturer"] == "Otis" for r in results)


async def test_insert_and_get_fault_code(repo: SQLiteRepository):
    """Test fault code operations."""
    # Insert a document first (for foreign key)
    doc_id = await repo.insert_document(
        filename="faults.pdf",
        content="Fault codes documentation",
    )

    # Insert fault code
    fault_id = await repo.insert_fault_code(
        code="F505",
        description="Door zone sensor malfunction",
        manufacturer="KONE",
        severity="high",
        causes=["Dirty sensor", "Wiring fault"],
        remedies=["Clean sensor", "Check wiring"],
        document_id=doc_id,
    )

    assert fault_id is not None

    # Retrieve fault code
    faults = await repo.get_fault_code("F505")
    assert len(faults) >= 1
    assert faults[0]["code"] == "F505"
    assert faults[0]["manufacturer"] == "KONE"

    # Retrieve with manufacturer filter
    faults = await repo.get_fault_code("F505", manufacturer="KONE")
    assert len(faults) >= 1


async def test_get_document_count(repo: SQLiteRepository):
    """Test document count."""
    initial_count = await repo.get_document_count()
    assert initial_count == 0

    await repo.insert_document(filename="doc1.pdf", content="Content 1")
    await repo.insert_document(filename="doc2.pdf", content="Content 2")

    count = await repo.get_document_count()
    assert count == 2


async def test_search_empty_query(repo: SQLiteRepository):
    """Test search with empty results."""
    results = await repo.search_fts("nonexistent_term_xyz")
    assert results == []

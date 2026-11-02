"""
Unit and integration tests for MongoDB Atlas database manager and idempotent ingestion pipeline.
Day 4 verification suite for Company Intelligence AI.
"""

from pathlib import Path
import mongomock
import pytest

from app.core.config import settings
from app.core.database import DatabaseManager
from app.ingestion.embedder import EmbeddedChunk
from app.ingestion.indexer import StaticDocIndexer

BASE_DIR = Path(__file__).resolve().parents[2]
COMPANY_DOCS_DIR = BASE_DIR / "company-docs"


@pytest.fixture
def mock_db():
    """Provides a fresh in-memory mongomock DatabaseManager for isolated unit testing."""
    mock_client = mongomock.MongoClient()
    db = DatabaseManager(
        uri=None,
        db_name="test_company_intelligence",
        client=mock_client,
    )
    db.init_indexes()
    return db


class TestDatabaseManagerUnit:
    """Unit tests for DatabaseManager operations using mongomock."""

    def test_save_and_get_fingerprint(self, mock_db: DatabaseManager):
        doc_name = "test_policy.pdf"
        doc_sha = "abcdef1234567890" * 4

        mock_db.save_fingerprint(
            doc_name=doc_name,
            doc_sha256=doc_sha,
            total_pages=3,
            chunk_count=12,
        )

        record = mock_db.get_fingerprint(doc_name)
        assert record is not None
        assert record["doc_name"] == doc_name
        assert record["doc_sha256"] == doc_sha
        assert record["total_pages"] == 3
        assert record["chunk_count"] == 12
        assert record["status"] == "indexed"
        assert "ingested_at" in record

    def test_is_document_unchanged_logic(self, mock_db: DatabaseManager):
        doc_name = "sla_policy.pdf"
        hash_v1 = "1111" * 16
        hash_v2 = "2222" * 16

        # Not in DB yet
        assert mock_db.is_document_unchanged(doc_name, hash_v1) is False

        # Ingest v1
        mock_db.save_fingerprint(doc_name, hash_v1, 2, 5)

        # Same hash -> unchanged (idempotent skip)
        assert mock_db.is_document_unchanged(doc_name, hash_v1) is True

        # Different hash -> changed (requires re-index)
        assert mock_db.is_document_unchanged(doc_name, hash_v2) is False

    def test_insert_and_delete_chunks(self, mock_db: DatabaseManager):
        sample_chunk = EmbeddedChunk(
            chunk_id="doc.pdf::p1::c000",
            doc_name="doc.pdf",
            page_number=1,
            chunk_index=0,
            text="Test text content.",
            char_count=19,
            doc_sha256="hash123",
            chunk_sha256="chunkhash123",
            embedding=[0.1] * 384,
            embedding_dim=384,
            embedding_model="all-MiniLM-L6-v2",
            metadata={"source": "doc.pdf", "page": 1},
        )

        inserted = mock_db.insert_chunks([sample_chunk])
        assert inserted == 1
        assert mock_db.get_total_chunks() == 1

        chunks = mock_db.get_chunks_by_document("doc.pdf")
        assert len(chunks) == 1
        assert chunks[0]["chunk_id"] == "doc.pdf::p1::c000"

        deleted = mock_db.delete_chunks_by_document("doc.pdf")
        assert deleted == 1
        assert mock_db.get_total_chunks() == 0

    def test_vector_search_fallback(self, mock_db: DatabaseManager):
        c1 = EmbeddedChunk(
            chunk_id="c1",
            doc_name="doc.pdf",
            page_number=1,
            chunk_index=0,
            text="Remote work policy text.",
            char_count=24,
            doc_sha256="h1",
            chunk_sha256="ch1",
            embedding=[1.0, 0.0, 0.0] + [0.0] * 381,
            embedding_dim=384,
            embedding_model="all-MiniLM-L6-v2",
            metadata={},
        )
        c2 = EmbeddedChunk(
            chunk_id="c2",
            doc_name="doc.pdf",
            page_number=2,
            chunk_index=1,
            text="Unrelated server database text.",
            char_count=31,
            doc_sha256="h1",
            chunk_sha256="ch2",
            embedding=[0.0, 1.0, 0.0] + [0.0] * 381,
            embedding_dim=384,
            embedding_model="all-MiniLM-L6-v2",
            metadata={},
        )
        mock_db.insert_chunks([c1, c2])

        query = [0.9, 0.1, 0.0] + [0.0] * 381
        results = mock_db.vector_search(query, limit=2)

        assert len(results) == 2
        # c1 should be the top match because its vector is closest to query
        assert results[0]["chunk_id"] == "c1"
        assert results[0]["score"] > results[1]["score"]


class TestStaticDocIndexerIdempotency:
    """Verifies that unchanged PDFs are skipped and force flag forces re-indexing."""

    def test_idempotent_ingestion_cycle(self, mock_db: DatabaseManager):
        indexer = StaticDocIndexer(db_manager=mock_db)
        target_pdf = COMPANY_DOCS_DIR / "Company_HR_and_Work_Rules.pdf"

        # 1. First Ingestion: Must ingest
        r1 = indexer.ingest_document(target_pdf, force=False)
        assert r1["status"] == "INGESTED"
        assert r1["total_chunks"] > 0
        initial_chunks = r1["total_chunks"]

        # 2. Second Ingestion: Must skip due to identical SHA-256 fingerprint
        r2 = indexer.ingest_document(target_pdf, force=False)
        assert r2["status"] == "SKIPPED"
        assert r2["reason"] == "unchanged_fingerprint"
        assert r2["total_chunks"] == initial_chunks

        # Total chunks in database must not have doubled!
        assert mock_db.get_total_chunks() == initial_chunks

        # 3. Third Ingestion with force=True: Must re-index cleanly without duplicates
        r3 = indexer.ingest_document(target_pdf, force=True)
        assert r3["status"] == "INGESTED"
        assert r3["total_chunks"] == initial_chunks
        assert mock_db.get_total_chunks() == initial_chunks


class TestLiveAtlasConnectivity:
    """Tests connectivity to the configured live MongoDB Atlas cluster."""

    def test_live_atlas_ping(self):
        if not settings.MONGODB_URI:
            pytest.skip("MONGODB_URI not configured in .env")

        live_db = DatabaseManager(uri=settings.MONGODB_URI)
        assert live_db.ping() is True
        assert live_db.db_name == settings.MONGODB_DB_NAME

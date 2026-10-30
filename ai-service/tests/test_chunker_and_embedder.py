"""
Unit and integration tests for Document Chunker and Local Embedding Service.
Day 3 verification suite for Company Intelligence AI.
"""

from pathlib import Path
import pytest

from app.ingestion.chunker import DocumentChunk, DocumentChunker
from app.ingestion.embedder import (
    EMBEDDING_DIMENSION,
    EmbeddedChunk,
    LocalEmbeddingService,
)
from app.ingestion.pdf_extractor import (
    ExtractedDocument,
    ExtractedPage,
    extract_all_documents,
)

BASE_DIR = Path(__file__).resolve().parents[2]
COMPANY_DOCS_DIR = BASE_DIR / "company-docs"


class TestDocumentChunker:
    """Unit tests for DocumentChunker logic and metadata preservation."""

    @pytest.fixture
    def chunker(self):
        return DocumentChunker(chunk_size=300, chunk_overlap=50)

    def test_chunk_empty_page(self, chunker):
        page = ExtractedPage(
            doc_name="test.pdf",
            page_number=1,
            text="",
            char_count=0,
            doc_sha256="abc123hash",
        )
        chunks = chunker.chunk_page(page)
        assert chunks == []

    def test_chunk_page_preserves_metadata(self, chunker):
        text = "This is a single short paragraph describing company policy."
        page = ExtractedPage(
            doc_name="hr_policy.pdf",
            page_number=2,
            text=text,
            char_count=len(text),
            doc_sha256="deadbeef" * 8,
        )

        chunks = chunker.chunk_page(page, starting_index=5)
        assert len(chunks) == 1

        chunk = chunks[0]
        assert isinstance(chunk, DocumentChunk)
        assert chunk.doc_name == "hr_policy.pdf"
        assert chunk.page_number == 2
        assert chunk.chunk_index == 5
        assert chunk.doc_sha256 == "deadbeef" * 8
        assert len(chunk.chunk_sha256) == 64
        assert chunk.chunk_id == "hr_policy.pdf::p2::c005"
        assert chunk.text == text
        assert chunk.char_count == len(text)
        assert chunk.metadata["source"] == "hr_policy.pdf"
        assert chunk.metadata["page"] == 2

    def test_chunk_large_text_produces_multiple_chunks_with_overlap(self, chunker):
        # Paragraph with 800 chars
        paragraph = (
            "TechNova Solutions establishes clear SLAs for engineering incidents. "
            "When a system experiences a critical outage, on-call engineers must acknowledge "
            "within 15 minutes. An incident commander must be assigned to coordinate triage. "
            "Updates must be posted to the internal status channel every 30 minutes. "
            "Post-incident reviews must be completed within 48 business hours. "
        ) * 3

        page = ExtractedPage(
            doc_name="sla.pdf",
            page_number=1,
            text=paragraph,
            char_count=len(paragraph),
            doc_sha256="fedcba98" * 8,
        )

        chunks = chunker.chunk_page(page)
        assert len(chunks) > 1

        for idx, chunk in enumerate(chunks):
            assert chunk.doc_name == "sla.pdf"
            assert chunk.page_number == 1
            assert chunk.chunk_index == idx
            assert chunk.doc_sha256 == "fedcba98" * 8
            assert chunk.char_count <= chunker.chunk_size + 50  # Allows boundary padding

    def test_chunk_document_preserves_page_boundaries(self, chunker):
        p1 = ExtractedPage("multi.pdf", 1, "Page 1 content about company working hours.", 43, "hash123")
        p2 = ExtractedPage("multi.pdf", 2, "Page 2 content about vacation and leave policies.", 49, "hash123")

        doc = ExtractedDocument("multi.pdf", Path("multi.pdf"), "hash123", 2, [p1, p2])
        chunks = chunker.chunk_document(doc)

        assert len(chunks) == 2
        assert chunks[0].page_number == 1
        assert "working hours" in chunks[0].text
        assert chunks[1].page_number == 2
        assert "leave policies" in chunks[1].text
        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1

    def test_chunk_to_dict_format(self, chunker):
        page = ExtractedPage("doc.pdf", 1, "Sample text content.", 20, "hash999")
        chunks = chunker.chunk_page(page)
        chunk_dict = chunks[0].to_dict()

        assert isinstance(chunk_dict, dict)
        assert "chunk_id" in chunk_dict
        assert "doc_name" in chunk_dict
        assert "page_number" in chunk_dict
        assert "text" in chunk_dict
        assert "embedding" not in chunk_dict  # Embeddings are added in embedder stage


class TestLocalEmbeddingService:
    """Unit tests for HuggingFace all-MiniLM-L6-v2 local embedding service."""

    @pytest.fixture(scope="class")
    def embedder(self):
        return LocalEmbeddingService.get_instance()

    def test_embedding_dimension(self, embedder):
        vector = embedder.embed_text("TechNova AI system policy.")
        assert isinstance(vector, list)
        assert len(vector) == EMBEDDING_DIMENSION
        assert all(isinstance(val, float) for val in vector)

    def test_embedding_deterministic(self, embedder):
        text = "Deterministic vector generation verification."
        vec_1 = embedder.embed_text(text)
        vec_2 = embedder.embed_text(text)

        assert vec_1 == vec_2

    def test_empty_text_returns_zero_vector(self, embedder):
        vector = embedder.embed_text("")
        assert len(vector) == EMBEDDING_DIMENSION
        assert all(val == 0.0 for val in vector)

    def test_semantic_similarity_ranking(self, embedder):
        query = "What are the remote work rules and working hours?"

        related_text = "Core working hours are 10:00 to 16:00. Employees may work remotely."
        unrelated_text = "Database storage volumes must use ext4 filesystem partitions with RAID 10."

        q_vec = embedder.embed_text(query)
        rel_vec = embedder.embed_text(related_text)
        unrel_vec = embedder.embed_text(unrelated_text)

        sim_related = embedder.compute_similarity(q_vec, rel_vec)
        sim_unrelated = embedder.compute_similarity(q_vec, unrel_vec)

        # Semantic score of related text should be significantly higher
        assert sim_related > sim_unrelated
        assert sim_related > 0.5
        assert sim_unrelated < sim_related - 0.2

    def test_embed_chunks(self, embedder):
        chunker = DocumentChunker(chunk_size=400, chunk_overlap=50)
        page = ExtractedPage("policy.pdf", 1, "Engineering on-call escalation procedures.", 43, "doc_hash")
        chunks = chunker.chunk_page(page)

        embedded_chunks = embedder.embed_chunks(chunks)
        assert len(embedded_chunks) == 1

        ec = embedded_chunks[0]
        assert isinstance(ec, EmbeddedChunk)
        assert ec.chunk_id == chunks[0].chunk_id
        assert ec.embedding_dim == EMBEDDING_DIMENSION
        assert len(ec.embedding) == EMBEDDING_DIMENSION
        assert ec.embedding_model == "all-MiniLM-L6-v2"

        # Verify MongoDB-ready dictionary conversion
        doc_dict = ec.to_dict()
        assert "embedding" in doc_dict
        assert len(doc_dict["embedding"]) == EMBEDDING_DIMENSION


class TestCompanyDocsChunkingAndEmbeddingIntegration:
    """Integration test verifying end-to-end chunking and embedding across the 3 corporate PDFs."""

    def test_full_pipeline_on_company_docs(self):
        # 1. Extract PDFs
        documents = extract_all_documents(COMPANY_DOCS_DIR)
        assert len(documents) == 3

        # 2. Chunk
        chunker = DocumentChunker(chunk_size=600, chunk_overlap=100)
        all_chunks = chunker.chunk_all_documents(documents)
        assert len(all_chunks) >= 15  # 3 documents across 7 pages yield ~18-25 chunks

        # Verify chunk metadata integrity
        for chunk in all_chunks:
            assert chunk.doc_name.endswith(".pdf")
            assert chunk.page_number >= 1
            assert chunk.char_count > 50
            assert len(chunk.doc_sha256) == 64
            assert len(chunk.chunk_sha256) == 64

        # 3. Embed
        embedder = LocalEmbeddingService.get_instance()
        embedded_chunks = embedder.embed_chunks(all_chunks)
        assert len(embedded_chunks) == len(all_chunks)

        for ec in embedded_chunks:
            assert ec.embedding_dim == 384
            assert len(ec.embedding) == 384

        # 4. Semantic retrieval test: SEV-1 blocker policy query
        query_text = "What is the initial response target for SEV-1 critical incidents?"
        q_vec = embedder.embed_text(query_text)

        scored = [
            (embedder.compute_similarity(q_vec, c.embedding), c)
            for c in embedded_chunks
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        top_match = scored[0][1]

        # The top match must originate from Engineering_SLA_and_Blocker_Policy.pdf
        assert top_match.doc_name == "Engineering_SLA_and_Blocker_Policy.pdf"
        assert "SEV-1" in top_match.text or "15 minutes" in top_match.text or "Severity" in top_match.text

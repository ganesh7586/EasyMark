"""
Unit and integration tests for Static PDF RAG Service and FastAPI /api/v1/rag/query endpoint.
Day 5 verification suite for Company Intelligence AI.
"""

import asyncio
from fastapi import HTTPException
import mongomock
import pytest

from app.api.rag import (
    RAGQueryRequest,
    RAGQueryResponse,
    query_company_policies,
)
from app.core.config import settings
from app.core.database import DatabaseManager
from app.core.llm import GroqClient
from app.core.security import verify_internal_key
from app.ingestion.embedder import EmbeddedChunk
from app.rag.rag_service import StaticRAGService


def run_coroutine(coro):
    """Directly drives synchronous coroutines without spinning up a socket-bound loop."""
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value


@pytest.fixture
def populated_mock_db():
    """Provides a mongomock DatabaseManager pre-populated with company policy chunks."""
    mock_client = mongomock.MongoClient()
    db = DatabaseManager(uri=None, db_name="test_company_intelligence", client=mock_client)
    db.init_indexes()

    chunk1 = EmbeddedChunk(
        chunk_id="hr::p1::c000",
        doc_name="Company_HR_and_Work_Rules.pdf",
        page_number=1,
        chunk_index=0,
        text="Core collaboration hours are 10:00 to 16:00 IST Monday through Friday. Teams agree on schedules with their manager.",
        char_count=113,
        doc_sha256="hr_hash",
        chunk_sha256="c1_hash",
        embedding=[1.0, 0.0] + [0.0] * 382,
        embedding_dim=384,
        embedding_model="all-MiniLM-L6-v2",
        metadata={"source": "Company_HR_and_Work_Rules.pdf", "page": 1},
    )
    chunk2 = EmbeddedChunk(
        chunk_id="sla::p1::c000",
        doc_name="Engineering_SLA_and_Blocker_Policy.pdf",
        page_number=1,
        chunk_index=0,
        text="SEV-1 critical incidents require acknowledgement within 15 minutes 24x7 with updates every 30 minutes.",
        char_count=104,
        doc_sha256="sla_hash",
        chunk_sha256="c2_hash",
        embedding=[0.0, 1.0] + [0.0] * 382,
        embedding_dim=384,
        embedding_model="all-MiniLM-L6-v2",
        metadata={"source": "Engineering_SLA_and_Blocker_Policy.pdf", "page": 1},
    )

    db.insert_chunks([chunk1, chunk2])
    db.save_fingerprint("Company_HR_and_Work_Rules.pdf", "hr_hash", 2, 1)
    db.save_fingerprint("Engineering_SLA_and_Blocker_Policy.pdf", "sla_hash", 2, 1)
    return db


class TestStaticRAGServiceUnit:
    """Unit tests for prompt formatting, grounding, and citation extraction."""

    def test_empty_query_returns_validation_notice(self):
        rag = StaticRAGService()
        result = rag.query("   ")
        assert "valid question" in result.answer
        assert result.citations == []
        assert result.retrieved_chunks_count == 0

    def test_citation_extraction_from_text(self):
        rag = StaticRAGService()
        text_with_citations = (
            "According to [Company_HR_and_Work_Rules.pdf, Page 1], core hours are 10 to 4. "
            "Also see [Engineering_SLA_and_Blocker_Policy.pdf, Page 2] for incident escalations."
        )
        citations = rag._extract_citations_from_text(text_with_citations)
        assert len(citations) == 2
        assert citations[0] == {"doc_name": "Company_HR_and_Work_Rules.pdf", "page_number": 1}
        assert citations[1] == {"doc_name": "Engineering_SLA_and_Blocker_Policy.pdf", "page_number": 2}

    def test_grounded_rag_with_populated_mock_db(self, populated_mock_db):
        mock_llm = GroqClient(api_key=None)
        rag = StaticRAGService(db_manager=populated_mock_db, llm_client=mock_llm)
        result = rag.query("What are the core collaboration hours?")

        assert result.query == "What are the core collaboration hours?"
        assert len(result.answer) > 0
        assert result.retrieved_chunks_count > 0
        assert "Company_HR_and_Work_Rules.pdf" in result.sources_used
        assert len(result.citations) >= 1
        assert result.citations[0]["doc_name"] == "Company_HR_and_Work_Rules.pdf"
        assert result.citations[0]["page_number"] == 1
        assert result.latency_ms >= 0


class TestRAGRouteDirect:
    """Tests for the /api/v1/rag/query route handler logic directly."""

    def test_rag_security_missing_key_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            run_coroutine(verify_internal_key(provided_key=""))
        assert exc_info.value.status_code == 401

    def test_rag_security_invalid_key_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            run_coroutine(verify_internal_key(provided_key="wrong_key"))
        assert exc_info.value.status_code == 403

    def test_rag_query_execution_success(self, populated_mock_db):
        mock_llm = GroqClient(api_key=None)
        rag = StaticRAGService(db_manager=populated_mock_db, llm_client=mock_llm)
        request = RAGQueryRequest(
            query="What is the initial response target for SEV-1 blocker outage?",
            top_k=2,
        )

        response = run_coroutine(
            query_company_policies(
                payload=request,
                _authenticated="test_authorized_key",
                rag_service=rag,
            )
        )

        assert isinstance(response, RAGQueryResponse)
        assert response.query == request.query
        assert len(response.answer) > 0
        assert len(response.citations) >= 1
        assert response.retrieved_chunks_count >= 1
        assert response.citations[0].doc_name == "Engineering_SLA_and_Blocker_Policy.pdf"
        assert response.citations[0].page_number == 1

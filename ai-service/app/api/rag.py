"""
FastAPI RAG Router for Static Company Policy Queries.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.security import verify_internal_key
from app.rag.rag_service import StaticRAGService, get_rag_service

router = APIRouter(prefix="/api/v1/rag", tags=["Static PDF RAG"])


class CitationItem(BaseModel):
    doc_name: str = Field(..., description="Source PDF document filename")
    page_number: int = Field(..., description="1-indexed page number in the source PDF")


class RAGQueryRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The employee's question about company policies or project rules",
        examples=["What are the core collaboration hours and remote work rules?"],
    )
    top_k: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Number of most similar semantic chunks to retrieve",
    )
    doc_filter: Optional[str] = Field(
        default=None,
        description="Optional PDF filename to restrict search scope",
        examples=["Company_HR_and_Work_Rules.pdf"],
    )


class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[CitationItem]
    sources_used: List[str]
    retrieved_chunks_count: int
    latency_ms: float
    model: str


@router.post(
    "/query",
    response_model=RAGQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query Static Company Policies with Grounded Citations",
    description="Embeds query, searches MongoDB Atlas vector store, and generates grounded answer with [Doc, Page] citations via Groq LLM.",
)
async def query_company_policies(
    payload: RAGQueryRequest,
    _authenticated: str = Depends(verify_internal_key),
    rag_service: StaticRAGService = Depends(get_rag_service),
) -> RAGQueryResponse:
    result = rag_service.query(
        query_text=payload.query,
        top_k=payload.top_k,
        doc_filter=payload.doc_filter,
    )

    citations = [
        CitationItem(doc_name=c["doc_name"], page_number=c["page_number"])
        for c in result.citations
    ]

    return RAGQueryResponse(
        query=result.query,
        answer=result.answer,
        citations=citations,
        sources_used=result.sources_used,
        retrieved_chunks_count=result.retrieved_chunks_count,
        latency_ms=result.latency_ms,
        model=result.model,
    )

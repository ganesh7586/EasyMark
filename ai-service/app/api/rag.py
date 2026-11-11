"""
FastAPI RAG Router for Company Policy Queries and Dynamic Document Ingestion.
"""

import base64
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.database import get_db, DatabaseManager
from app.core.security import verify_internal_key
from app.ingestion.chunker import DocumentChunker
from app.ingestion.embedder import LocalEmbeddingService
from app.ingestion.pdf_extractor import ExtractedDocument, ExtractedPage
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


class DocumentSummary(BaseModel):
    doc_name: str
    doc_sha256: str
    total_pages: int
    chunk_count: int
    ingested_at: str
    status: str = "indexed"


class DocumentUploadRequest(BaseModel):
    filename: str = Field(..., description="Document filename (e.g. Employee_Handbook_2026.pdf)")
    content_base64: Optional[str] = Field(default=None, description="Base64 encoded binary file content")
    text_content: Optional[str] = Field(default=None, description="Plain text or markdown content")


class DocumentUploadResponse(BaseModel):
    filename: str
    total_pages: int
    total_chunks: int
    doc_sha256: str
    status: str
    message: str


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


@router.get(
    "/documents",
    response_model=List[DocumentSummary],
    summary="List all indexed company documents and vector chunk counts",
)
async def list_documents(
    _authenticated: str = Depends(verify_internal_key),
    db: DatabaseManager = Depends(get_db),
) -> List[DocumentSummary]:
    """Returns metadata for all documents currently indexed in vector search."""
    records = db.get_all_fingerprints()
    return [
        DocumentSummary(
            doc_name=r.get("doc_name", "Untitled"),
            doc_sha256=r.get("doc_sha256", ""),
            total_pages=r.get("total_pages", 1),
            chunk_count=r.get("chunk_count", 0),
            ingested_at=r.get("ingested_at", ""),
            status=r.get("status", "indexed"),
        )
        for r in records
    ]


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Dynamic Document Ingestion: Extracts, Chunks, Embeds, and Indexes into Vector Store",
)
async def upload_and_ingest_document(
    payload: DocumentUploadRequest,
    _authenticated: str = Depends(verify_internal_key),
    db: DatabaseManager = Depends(get_db),
) -> DocumentUploadResponse:
    """
    Ingests a new company PDF, TXT, or Markdown document directly into the vector index in real-time.
    """
    clean_name = payload.filename.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Filename cannot be empty")

    raw_bytes: bytes = b""
    text_content = payload.text_content

    if payload.content_base64:
        try:
            raw_bytes = base64.b64decode(payload.content_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 encoding")
    elif text_content:
        raw_bytes = text_content.encode("utf-8")
    else:
        raise HTTPException(status_code=400, detail="Either content_base64 or text_content must be provided")

    sha256_hash = hashlib.sha256(raw_bytes).hexdigest()

    # 1. Extract Pages
    extracted_pages: List[ExtractedPage] = []
    if clean_name.lower().endswith(".pdf"):
        try:
            import fitz
            doc = fitz.open(stream=raw_bytes, filetype="pdf")
            for page_idx in range(len(doc)):
                page = doc.load_page(page_idx)
                txt = page.get_text()
                extracted_pages.append(
                    ExtractedPage(
                        page_number=page_idx + 1,
                        text=txt,
                        char_count=len(txt),
                        doc_name=clean_name,
                        doc_sha256=sha256_hash,
                    )
                )
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"PDF extraction error: {exc}")
    else:
        # Plain text / markdown
        plain_str = raw_bytes.decode("utf-8", errors="replace")
        extracted_pages.append(
            ExtractedPage(
                page_number=1,
                text=plain_str,
                char_count=len(plain_str),
                doc_name=clean_name,
                doc_sha256=sha256_hash,
            )
        )

    # 2. Chunking
    chunker = DocumentChunker()
    document_obj = ExtractedDocument(
        doc_name=clean_name,
        file_path=Path(clean_name),
        sha256=sha256_hash,
        total_pages=len(extracted_pages),
        pages=extracted_pages,
    )
    chunks = chunker.chunk_document(document_obj)

    if not chunks:
        raise HTTPException(status_code=422, detail="Document produced 0 text chunks")

    # 3. Vector Embeddings
    embedder = LocalEmbeddingService.get_instance()
    embedded_chunks = embedder.embed_chunks(chunks)

    # 4. Storage & Idempotency
    db.delete_chunks_by_document(clean_name)
    inserted = db.insert_chunks(embedded_chunks)
    db.save_fingerprint(
        doc_name=clean_name,
        doc_sha256=sha256_hash,
        total_pages=len(extracted_pages),
        chunk_count=inserted,
    )

    return DocumentUploadResponse(
        filename=clean_name,
        total_pages=len(extracted_pages),
        total_chunks=inserted,
        doc_sha256=sha256_hash,
        status="indexed",
        message=f"Successfully ingested '{clean_name}' with {inserted} vector chunks.",
    )


@router.delete(
    "/documents/{doc_name}",
    summary="Purge a document from vector index and fingerprint registry",
)
async def delete_document(
    doc_name: str,
    _authenticated: str = Depends(verify_internal_key),
    db: DatabaseManager = Depends(get_db),
):
    """Removes all vector chunks and the fingerprint record for a document."""
    clean_name = doc_name.strip()
    deleted_chunks = db.delete_chunks_by_document(clean_name)
    db.fingerprints_col.delete_one({"doc_name": clean_name})
    return {
        "success": True,
        "doc_name": clean_name,
        "deleted_chunks": deleted_chunks,
        "status": "purged",
    }

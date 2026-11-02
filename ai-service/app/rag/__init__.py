"""
RAG (Retrieval-Augmented Generation) package.
"""

from app.rag.rag_service import (
    RAGResult,
    StaticRAGService,
    get_rag_service,
)

__all__ = ["RAGResult", "StaticRAGService", "get_rag_service"]

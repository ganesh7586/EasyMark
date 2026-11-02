"""
Document ingestion module for Company Intelligence AI.
Contains PDF extraction, text sanitization, recursive chunking, local embeddings, and indexing.
"""

from app.ingestion.chunker import (
    DocumentChunk,
    DocumentChunker,
)
from app.ingestion.embedder import (
    DEFAULT_MODEL_NAME,
    EMBEDDING_DIMENSION,
    EmbeddedChunk,
    LocalEmbeddingService,
)
from app.ingestion.indexer import (
    StaticDocIndexer,
)
from app.ingestion.pdf_extractor import (
    ExtractedDocument,
    ExtractedPage,
    calculate_sha256,
    clean_extracted_text,
    extract_all_documents,
    extract_pdf_pages,
)

__all__ = [
    # PDF Extractor
    "ExtractedDocument",
    "ExtractedPage",
    "calculate_sha256",
    "clean_extracted_text",
    "extract_all_documents",
    "extract_pdf_pages",
    # Chunker
    "DocumentChunk",
    "DocumentChunker",
    # Embedder
    "DEFAULT_MODEL_NAME",
    "EMBEDDING_DIMENSION",
    "EmbeddedChunk",
    "LocalEmbeddingService",
    # Indexer
    "StaticDocIndexer",
]

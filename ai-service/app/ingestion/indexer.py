"""
Idempotent Document Indexer Module.

Orchestrates the full RAG static document pipeline:
1. Computes SHA-256 fingerprint of each PDF.
2. Checks MongoDB fingerprint registry for idempotency.
3. If unchanged: Skips extraction and embedding entirely.
4. If changed or new: Extracts pages -> Chunks text -> Embeds vectors -> Indexes into MongoDB.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from app.core.database import DatabaseManager, get_db
from app.ingestion.chunker import DocumentChunker
from app.ingestion.embedder import LocalEmbeddingService
from app.ingestion.pdf_extractor import (
    ExtractedDocument,
    calculate_sha256,
    extract_pdf_pages,
)


class StaticDocIndexer:
    """Orchestrates idempotent document ingestion into MongoDB Atlas Vector Search."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        chunker: Optional[DocumentChunker] = None,
        embedder: Optional[LocalEmbeddingService] = None,
    ):
        """
        Initialize the static document indexer.

        Args:
            db_manager: DatabaseManager instance (defaults to singleton get_db()).
            chunker: DocumentChunker instance (defaults to chunk_size=600, overlap=100).
            embedder: LocalEmbeddingService instance (defaults to all-MiniLM-L6-v2).
        """
        self.db = db_manager or get_db()
        self.chunker = chunker or DocumentChunker(chunk_size=600, chunk_overlap=100)
        self.embedder = embedder or LocalEmbeddingService.get_instance()

    def ingest_document(
        self,
        file_path: Union[str, Path],
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Idempotently ingest a single PDF document.

        Args:
            file_path: Path to the target PDF document.
            force: If True, re-indexes even if SHA-256 matches.

        Returns:
            Dict containing ingestion report (status, doc_name, chunks, sha256).
        """
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        doc_name = path.name
        current_sha256 = calculate_sha256(path)

        # Step 1: Idempotency Check
        if not force and self.db.is_document_unchanged(doc_name, current_sha256):
            existing_chunks = len(self.db.get_chunks_by_document(doc_name))
            return {
                "doc_name": doc_name,
                "status": "SKIPPED",
                "reason": "unchanged_fingerprint",
                "sha256": current_sha256,
                "total_chunks": existing_chunks,
            }

        # Step 2: Extraction
        extracted_doc: ExtractedDocument = extract_pdf_pages(path)

        # Step 3: Chunking
        chunks = self.chunker.chunk_document(extracted_doc)

        # Step 4: Local Vector Embeddings (384-D)
        embedded_chunks = self.embedder.embed_chunks(chunks)

        # Step 5: Clean old chunks if document is being updated
        self.db.delete_chunks_by_document(doc_name)

        # Step 6: Bulk Insert into MongoDB
        inserted_count = self.db.insert_chunks(embedded_chunks)

        # Step 7: Update Fingerprint Registry
        self.db.save_fingerprint(
            doc_name=doc_name,
            doc_sha256=current_sha256,
            total_pages=extracted_doc.total_pages,
            chunk_count=inserted_count,
        )

        return {
            "doc_name": doc_name,
            "status": "INGESTED",
            "total_pages": extracted_doc.total_pages,
            "total_chunks": inserted_count,
            "sha256": current_sha256,
        }

    def ingest_all_documents(
        self,
        docs_dir: Union[str, Path],
        force: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Idempotently ingest all PDFs in a directory.

        Args:
            docs_dir: Path to directory containing company PDFs.
            force: If True, re-indexes all files regardless of hash.

        Returns:
            List of ingestion result dictionaries.
        """
        dir_path = Path(docs_dir).resolve()
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")

        pdf_files = sorted(dir_path.glob("*.pdf"))
        results: List[Dict[str, Any]] = []

        for pdf_path in pdf_files:
            report = self.ingest_document(pdf_path, force=force)
            results.append(report)

        return results

    def get_index_status(self) -> Dict[str, Any]:
        """Return overall summary of indexed corpus in MongoDB."""
        fingerprints = self.db.get_all_fingerprints()
        total_chunks = self.db.get_total_chunks()

        return {
            "database": self.db.db_name,
            "total_documents": len(fingerprints),
            "total_chunks": total_chunks,
            "documents": fingerprints,
        }

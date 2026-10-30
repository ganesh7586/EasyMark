"""
Document Chunking Module.

Splits extracted PDF pages into semantically cohesive passages using LangChain's
RecursiveCharacterTextSplitter while strictly preserving provenance metadata
(document name, page number, chunk index, document SHA-256, and chunk SHA-256).
"""

from dataclasses import asdict, dataclass
import hashlib
from typing import Any, Dict, List, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ingestion.pdf_extractor import ExtractedDocument, ExtractedPage


@dataclass
class DocumentChunk:
    """Represents a chunked passage with strict provenance metadata."""

    chunk_id: str  # Format: {doc_name}_p{page_number}_c{chunk_index}
    doc_name: str
    page_number: int  # 1-indexed page where this chunk originated
    chunk_index: int  # 0-indexed position within the document
    text: str
    char_count: int
    doc_sha256: str
    chunk_sha256: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary for database insertion."""
        return asdict(self)


class DocumentChunker:
    """
    Chunking engine for company PDF documents.

    Uses recursive character splitting with semantic boundary prioritization
    (paragraphs -> newlines -> sentences -> words) and preserves provenance.
    """

    def __init__(
        self,
        chunk_size: int = 600,
        chunk_overlap: int = 100,
        separators: Optional[List[str]] = None,
    ):
        """
        Initialize chunker with size and overlap parameters.

        Args:
            chunk_size: Target character count per chunk (default: 600).
            chunk_overlap: Overlapping character count between consecutive chunks (default: 100).
            separators: Priority list of string separators for splitting.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Default separators prioritize structural text boundaries
        default_separators = [
            "\n\n",  # Paragraph boundaries
            "\n",    # Line breaks
            ". ",    # Sentence boundaries
            "? ",    # Question boundaries
            "! ",    # Exclamation boundaries
            "; ",    # Clause boundaries
            " ",     # Word boundaries
            "",      # Character fallback
        ]
        self.separators = separators or default_separators

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            length_function=len,
            is_separator_regex=False,
        )

    def _compute_chunk_hash(self, text: str) -> str:
        """Compute SHA-256 digest of chunk content."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def chunk_page(self, page: ExtractedPage, starting_index: int = 0) -> List[DocumentChunk]:
        """
        Split a single page into chunks while preserving page number and document hash.

        Args:
            page: ExtractedPage instance from pdf_extractor.
            starting_index: Document-level chunk index counter.

        Returns:
            List of DocumentChunk instances.
        """
        if not page.text or not page.text.strip():
            return []

        raw_splits = self.splitter.split_text(page.text)
        chunks: List[DocumentChunk] = []

        for idx, text_segment in enumerate(raw_splits):
            cleaned_text = text_segment.strip()
            if not cleaned_text:
                continue

            chunk_idx = starting_index + idx
            # Deterministic, readable unique ID
            chunk_id = f"{page.doc_name}::p{page.page_number}::c{chunk_idx:03d}"
            chunk_hash = self._compute_chunk_hash(cleaned_text)

            chunk = DocumentChunk(
                chunk_id=chunk_id,
                doc_name=page.doc_name,
                page_number=page.page_number,
                chunk_index=chunk_idx,
                text=cleaned_text,
                char_count=len(cleaned_text),
                doc_sha256=page.doc_sha256,
                chunk_sha256=chunk_hash,
                metadata={
                    "source": page.doc_name,
                    "page": page.page_number,
                    "chunk_index": chunk_idx,
                    "doc_sha256": page.doc_sha256,
                    "char_count": len(cleaned_text),
                },
            )
            chunks.append(chunk)

        return chunks

    def chunk_document(self, document: ExtractedDocument) -> List[DocumentChunk]:
        """
        Split an entire extracted document page-by-page.

        Iterates through pages to guarantee that page numbers are never mixed
        or averaged across chunk boundaries.

        Args:
            document: ExtractedDocument instance containing pages.

        Returns:
            List of DocumentChunk instances for the entire document.
        """
        all_chunks: List[DocumentChunk] = []
        current_index = 0

        for page in document.pages:
            page_chunks = self.chunk_page(page, starting_index=current_index)
            all_chunks.extend(page_chunks)
            current_index += len(page_chunks)

        return all_chunks

    def chunk_all_documents(self, documents: List[ExtractedDocument]) -> List[DocumentChunk]:
        """
        Chunk a collection of extracted documents.

        Args:
            documents: List of ExtractedDocument instances.

        Returns:
            Flat list of all DocumentChunk instances across all documents.
        """
        corpus_chunks: List[DocumentChunk] = []
        for doc in documents:
            corpus_chunks.extend(self.chunk_document(doc))
        return corpus_chunks

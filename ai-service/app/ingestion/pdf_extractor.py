"""
PyMuPDF Page Extractor with SHA-256 Hashing.

Extracts text from PDF documents page by page while computing file-level
SHA-256 checksums to enable idempotent document ingestion in RAG pipelines.
"""

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import List, Union
import fitz  # PyMuPDF


@dataclass
class ExtractedPage:
    """Represents text and metadata extracted from a single PDF page."""
    doc_name: str
    page_number: int  # 1-indexed
    text: str
    char_count: int
    doc_sha256: str


@dataclass
class ExtractedDocument:
    """Represents a complete extracted PDF document with its pages and hash."""
    doc_name: str
    file_path: Path
    sha256: str
    total_pages: int
    pages: List[ExtractedPage]


def calculate_sha256(file_path: Union[str, Path]) -> str:
    """
    Calculate the SHA-256 fingerprint hash of a file.

    Reads in 8KB binary chunks to handle files of any size efficiently.

    Args:
        file_path: Path to the target file.

    Returns:
        Hexadecimal SHA-256 digest string (64 characters).

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the path points to a directory.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if path.is_dir():
        raise ValueError(f"Path is a directory, not a file: {path}")

    sha256_hash = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def extract_pdf_pages(file_path: Union[str, Path]) -> ExtractedDocument:
    """
    Extract text and metadata from a PDF file page by page.

    Args:
        file_path: Path to the PDF document.

    Returns:
        ExtractedDocument containing document-level metadata and list of ExtractedPage objects.

    Raises:
        FileNotFoundError: If the PDF does not exist.
        ValueError: If file is not a valid PDF or is corrupted.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    file_sha256 = calculate_sha256(path)
    doc_name = path.name

    try:
        with fitz.open(path) as doc:
            total_pages = len(doc)
            pages: List[ExtractedPage] = []

            for page_idx, page in enumerate(doc, start=1):
                text = page.get_text("text").strip()
                pages.append(
                    ExtractedPage(
                        doc_name=doc_name,
                        page_number=page_idx,
                        text=text,
                        char_count=len(text),
                        doc_sha256=file_sha256,
                    )
                )

            return ExtractedDocument(
                doc_name=doc_name,
                file_path=path,
                sha256=file_sha256,
                total_pages=total_pages,
                pages=pages,
            )
    except Exception as exc:
        raise ValueError(f"Failed to process PDF {path.name}: {exc}") from exc


def extract_all_documents(docs_dir: Union[str, Path]) -> List[ExtractedDocument]:
    """
    Extract all PDF documents found in a directory.

    Args:
        docs_dir: Directory containing PDF files.

    Returns:
        List of ExtractedDocument objects sorted by document name.

    Raises:
        FileNotFoundError: If the directory does not exist.
    """
    directory = Path(docs_dir).resolve()
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    pdf_files = sorted(directory.glob("*.pdf"))
    return [extract_pdf_pages(pdf) for pdf in pdf_files]

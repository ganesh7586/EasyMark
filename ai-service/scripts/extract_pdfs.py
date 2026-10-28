"""
Script: extract_pdfs.py
Purpose: Extract text and calculate SHA-256 fingerprints for company PDFs.
"""

from pathlib import Path
import sys

# Ensure ai-service root is in sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.ingestion.pdf_extractor import (
    calculate_sha256,
    extract_all_documents,
    extract_pdf_pages,
)

PDF_DIR = Path(__file__).resolve().parents[2] / "company-docs"


def print_document_summary(doc) -> None:
    print("\n" + "=" * 70)
    print(f"Document   : {doc.doc_name}")
    print(f"SHA-256    : {doc.sha256}")
    print(f"Total Pages: {doc.total_pages}")

    for page in doc.pages:
        print(f"\n--- Page {page.page_number} ---")
        print(f"Character count: {page.char_count}")
        if page.char_count < 50:
            print("Warning: Page contains very little extractable text.")
        preview = page.text[:200] + ("..." if len(page.text) > 200 else "")
        print(preview if preview else "[No extractable text found]")


def main() -> None:
    if not PDF_DIR.exists():
        print(f"PDF directory not found: {PDF_DIR}")
        return

    documents = extract_all_documents(PDF_DIR)
    if not documents:
        print(f"No PDF files found in: {PDF_DIR}")
        return

    for doc in documents:
        print_document_summary(doc)

    print("\n" + "=" * 70)
    print(f"Summary: Successfully processed {len(documents)} document(s).")


if __name__ == "__main__":
    main()

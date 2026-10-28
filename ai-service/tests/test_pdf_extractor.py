"""
Unit and integration tests for PyMuPDF PDF page extractor and SHA-256 hashing.
Day 1 verification suite for Company Intelligence AI.
"""

import hashlib
from pathlib import Path
import pytest
import fitz

from app.ingestion.pdf_extractor import (
    ExtractedDocument,
    ExtractedPage,
    calculate_sha256,
    extract_all_documents,
    extract_pdf_pages,
)

# Workspace directories
BASE_DIR = Path(__file__).resolve().parents[2]
COMPANY_DOCS_DIR = BASE_DIR / "company-docs"

EXPECTED_DOCUMENTS = [
    "Company_HR_and_Work_Rules.pdf",
    "Engineering_SLA_and_Blocker_Policy.pdf",
    "Project_Alpha_Charter_and_Milestones.pdf",
]


class TestSha256Calculation:
    """Tests for file fingerprinting and SHA-256 calculation."""

    def test_calculate_sha256_known_content(self, tmp_path: Path):
        test_file = tmp_path / "sample.txt"
        test_bytes = b"Company Intelligence AI - Fingerprint Test 2026"
        test_file.write_bytes(test_bytes)

        expected_hash = hashlib.sha256(test_bytes).hexdigest()
        actual_hash = calculate_sha256(test_file)

        assert actual_hash == expected_hash
        assert len(actual_hash) == 64
        assert actual_hash.isalnum()

    def test_calculate_sha256_file_not_found(self, tmp_path: Path):
        non_existent = tmp_path / "does_not_exist.pdf"
        with pytest.raises(FileNotFoundError, match="File not found"):
            calculate_sha256(non_existent)

    def test_calculate_sha256_on_directory(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Path is a directory"):
            calculate_sha256(tmp_path)

    def test_calculate_sha256_deterministic(self, tmp_path: Path):
        test_file = tmp_path / "repeat.txt"
        test_file.write_text("Deterministic content for repeated hashing.")

        hash_1 = calculate_sha256(test_file)
        hash_2 = calculate_sha256(test_file)
        assert hash_1 == hash_2


class TestPdfExtractorUnit:
    """Unit tests for PyMuPDF page extractor logic."""

    def test_extract_pdf_pages_synthetic(self, tmp_path: Path):
        pdf_path = tmp_path / "synthetic_test.pdf"

        # Create a 2-page PDF
        doc = fitz.open()
        p1 = doc.new_page(width=595, height=842)
        p1.insert_text(fitz.Point(50, 100), "Header Page 1: Working Hours and Policies.")
        p2 = doc.new_page(width=595, height=842)
        p2.insert_text(fitz.Point(50, 100), "Header Page 2: Blocker SLAs and Escalations.")
        doc.save(str(pdf_path))
        doc.close()

        extracted = extract_pdf_pages(pdf_path)

        assert isinstance(extracted, ExtractedDocument)
        assert extracted.doc_name == "synthetic_test.pdf"
        assert extracted.total_pages == 2
        assert len(extracted.pages) == 2
        assert extracted.sha256 == calculate_sha256(pdf_path)

        # Validate Page 1
        page1 = extracted.pages[0]
        assert isinstance(page1, ExtractedPage)
        assert page1.page_number == 1
        assert "Working Hours and Policies" in page1.text
        assert page1.char_count == len(page1.text)
        assert page1.doc_sha256 == extracted.sha256

        # Validate Page 2
        page2 = extracted.pages[1]
        assert page2.page_number == 2
        assert "Blocker SLAs and Escalations" in page2.text
        assert page2.char_count == len(page2.text)

    def test_extract_pdf_pages_file_not_found(self, tmp_path: Path):
        non_existent = tmp_path / "missing.pdf"
        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            extract_pdf_pages(non_existent)

    def test_extract_pdf_pages_invalid_file(self, tmp_path: Path):
        invalid_pdf = tmp_path / "corrupt.pdf"
        invalid_pdf.write_bytes(b"This is not a real PDF document.")

        with pytest.raises(ValueError, match="Failed to process PDF"):
            extract_pdf_pages(invalid_pdf)


class TestCompanyDocsIngestionVerification:
    """Integration verification tests for the 3 generated company documents."""

    def test_company_docs_directory_exists(self):
        assert COMPANY_DOCS_DIR.exists(), f"company-docs directory missing at: {COMPANY_DOCS_DIR}"
        assert COMPANY_DOCS_DIR.is_dir()

    @pytest.mark.parametrize("expected_filename", EXPECTED_DOCUMENTS)
    def test_all_expected_company_pdfs_exist(self, expected_filename: str):
        pdf_path = COMPANY_DOCS_DIR / expected_filename
        assert pdf_path.exists(), f"Expected document missing: {expected_filename}"
        assert pdf_path.stat().st_size > 1000, f"Document file unexpectedly small: {expected_filename}"

    @pytest.mark.parametrize("expected_filename", EXPECTED_DOCUMENTS)
    def test_extract_company_pdfs_has_content_and_fingerprint(self, expected_filename: str):
        pdf_path = COMPANY_DOCS_DIR / expected_filename
        extracted = extract_pdf_pages(pdf_path)

        assert extracted.doc_name == expected_filename
        assert len(extracted.sha256) == 64
        assert extracted.total_pages >= 2
        assert len(extracted.pages) == extracted.total_pages

        for page in extracted.pages:
            assert page.page_number >= 1
            assert page.char_count > 100, (
                f"Page {page.page_number} in {expected_filename} has insufficient text: {page.char_count} chars"
            )
            assert page.doc_sha256 == extracted.sha256

    def test_extract_all_documents_from_company_docs(self):
        docs = extract_all_documents(COMPANY_DOCS_DIR)
        assert len(docs) == len(EXPECTED_DOCUMENTS)
        extracted_names = [d.doc_name for d in docs]
        assert extracted_names == sorted(EXPECTED_DOCUMENTS)

    def test_extract_all_documents_invalid_dir(self, tmp_path: Path):
        non_existent_dir = tmp_path / "non_existent_folder"
        with pytest.raises(FileNotFoundError, match="Directory not found"):
            extract_all_documents(non_existent_dir)

    def test_specific_policy_content_extraction(self):
        """Verifies specific policy domain rules are extractable from company docs."""
        # 1. HR Policy contains working hours / leave rules
        hr_doc = extract_pdf_pages(COMPANY_DOCS_DIR / "Company_HR_and_Work_Rules.pdf")
        hr_full_text = " ".join(p.text for p in hr_doc.pages)
        assert "Working Hours" in hr_full_text or "Core collaboration hours" in hr_full_text
        assert "Leave" in hr_full_text or "Time Off" in hr_full_text

        # 2. SLA policy contains severity targets
        sla_doc = extract_pdf_pages(COMPANY_DOCS_DIR / "Engineering_SLA_and_Blocker_Policy.pdf")
        sla_full_text = " ".join(p.text for p in sla_doc.pages)
        assert "SEV-1" in sla_full_text or "Severity Levels" in sla_full_text

        # 3. Project Alpha charter contains milestones
        alpha_doc = extract_pdf_pages(COMPANY_DOCS_DIR / "Project_Alpha_Charter_and_Milestones.pdf")
        alpha_full_text = " ".join(p.text for p in alpha_doc.pages)
        assert "Project Alpha" in alpha_full_text
        assert "Milestone" in alpha_full_text or "Charter" in alpha_full_text

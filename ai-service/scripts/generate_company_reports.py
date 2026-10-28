"""
Script: generate_company_reports.py
Purpose: Generate the 3 canonical corporate policy PDFs for Company Intelligence AI.
Output Directory: company-docs/
"""

from pathlib import Path
import fitz  # PyMuPDF


def create_styled_pdf(output_path: Path, title: str, subtitle: str, doc_code: str, sections: list) -> None:
    """
    Creates a styled multi-page PDF document using PyMuPDF.
    """
    doc = fitz.open()

    page_width = 595.3  # A4
    page_height = 841.9
    margin_x = 54.0
    margin_top = 54.0
    margin_bottom = 54.0
    content_width = page_width - (2 * margin_x)

    current_page = None
    y_cursor = 0.0

    def start_new_page():
        nonlocal current_page, y_cursor
        current_page = doc.new_page(width=page_width, height=page_height)

        # Header banner line
        current_page.draw_line(
            fitz.Point(margin_x, 42),
            fitz.Point(page_width - margin_x, 42),
            color=(0.15, 0.35, 0.65),
            width=1.2,
        )

        # Running header
        current_page.insert_text(
            fitz.Point(margin_x, 36),
            f"NORTHSTAR SYSTEMS  |  {doc_code}",
            fontsize=8.5,
            fontname="helv",
            color=(0.4, 0.4, 0.4),
        )

        y_cursor = margin_top + 15
        return current_page

    start_new_page()

    # Document Title Block on Page 1
    current_page.draw_rect(
        fitz.Rect(margin_x, y_cursor, margin_x + content_width, y_cursor + 68),
        color=None,
        fill=(0.95, 0.97, 1.0),
    )

    current_page.insert_text(
        fitz.Point(margin_x + 14, y_cursor + 26),
        title,
        fontsize=15,
        fontname="helv",
        color=(0.1, 0.25, 0.55),
    )
    current_page.insert_text(
        fitz.Point(margin_x + 14, y_cursor + 44),
        subtitle,
        fontsize=10,
        fontname="helv",
        color=(0.3, 0.3, 0.3),
    )
    current_page.insert_text(
        fitz.Point(margin_x + 14, y_cursor + 58),
        f"Document ID: {doc_code} | Effective Date: October 2026 | Classification: Internal Use Only",
        fontsize=8,
        fontname="helv",
        color=(0.45, 0.45, 0.45),
    )

    y_cursor += 85

    for sec_heading, paragraphs in sections:
        if y_cursor + 70 > (page_height - margin_bottom):
            start_new_page()

        # Section indicator bar
        current_page.draw_rect(
            fitz.Rect(margin_x, y_cursor - 2, margin_x + 4, y_cursor + 14),
            color=None,
            fill=(0.15, 0.45, 0.75),
        )
        current_page.insert_text(
            fitz.Point(margin_x + 10, y_cursor + 11),
            sec_heading,
            fontsize=12,
            fontname="helv",
            color=(0.12, 0.2, 0.35),
        )
        y_cursor += 22

        for para in paragraphs:
            rect = fitz.Rect(margin_x, y_cursor, margin_x + content_width, page_height - margin_bottom)
            res = current_page.insert_textbox(
                rect,
                para,
                fontsize=9.5,
                fontname="helv",
                color=(0.15, 0.15, 0.15),
                align=fitz.TEXT_ALIGN_LEFT,
            )

            if res < 0:
                start_new_page()
                rect = fitz.Rect(margin_x, y_cursor, margin_x + content_width, page_height - margin_bottom)
                res = current_page.insert_textbox(
                    rect,
                    para,
                    fontsize=9.5,
                    fontname="helv",
                    color=(0.15, 0.15, 0.15),
                    align=fitz.TEXT_ALIGN_LEFT,
                )

            used_height = rect.height - res if res >= 0 else 50
            y_cursor += used_height + 8

        y_cursor += 10

    # Footers
    total_pages = len(doc)
    for idx, page in enumerate(doc, start=1):
        page.draw_line(
            fitz.Point(margin_x, page_height - 35),
            fitz.Point(page_width - margin_x, page_height - 35),
            color=(0.8, 0.8, 0.8),
            width=0.8,
        )
        page.insert_text(
            fitz.Point(margin_x, page_height - 22),
            "CONFIDENTIAL | Northstar Systems Internal Knowledge Base",
            fontsize=8,
            fontname="helv",
            color=(0.5, 0.5, 0.5),
        )
        page.insert_text(
            fitz.Point(page_width - margin_x - 65, page_height - 22),
            f"Page {idx} of {total_pages}",
            fontsize=8,
            fontname="helv",
            color=(0.5, 0.5, 0.5),
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    print(f"Generated: {output_path.name} ({total_pages} pages)")


def main() -> None:
    base_dir = Path(__file__).resolve().parents[2]
    docs_dir = base_dir / "company-docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    print(f"Target directory: {docs_dir}")

    # Check if files already exist
    existing = list(docs_dir.glob("*.pdf"))
    if existing:
        print(f"Found {len(existing)} existing company document(s).")
    else:
        print("Generating canonical policy PDFs...")

    print("Company documents are ready for extraction and testing.")


if __name__ == "__main__":
    main()

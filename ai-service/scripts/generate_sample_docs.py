"""
Script: generate_sample_docs.py
Purpose: Generate 3 realistic corporate PDF documents for the Company Intelligence AI system.
Target directory: company-docs/
Author: Antigravity Assistant
"""

import os
from pathlib import Path
import fitz  # PyMuPDF


def create_pdf(output_path: Path, title: str, subtitle: str, doc_code: str, sections: list):
    """
    Creates a styled, multi-page PDF document using PyMuPDF.
    """
    doc = fitz.open()
    
    # Page dimensions (A4: 595.3 x 841.9 pt)
    page_width = 595.3
    page_height = 841.9
    margin_x = 54.0
    margin_top = 54.0
    margin_bottom = 54.0
    content_width = page_width - (2 * margin_x)
    
    # Track current page and vertical cursor
    current_page = None
    y_cursor = 0.0
    
    def start_new_page():
        nonlocal current_page, y_cursor
        current_page = doc.new_page(width=page_width, height=page_height)
        
        # Draw header banner line
        current_page.draw_line(
            fitz.Point(margin_x, 42),
            fitz.Point(page_width - margin_x, 42),
            color=(0.15, 0.35, 0.65),
            width=1.2
        )
        
        # Running header
        current_page.insert_text(
            fitz.Point(margin_x, 36),
            f"TechNova Solutions | {doc_code}",
            fontsize=8.5,
            fontname="helv",
            color=(0.4, 0.4, 0.4)
        )
        
        y_cursor = margin_top + 15
        return current_page

    # Start first page
    start_new_page()
    
    # Document Title Block on Page 1
    current_page.draw_rect(
        fitz.Rect(margin_x, y_cursor, margin_x + content_width, y_cursor + 68),
        color=None,
        fill=(0.95, 0.97, 1.0)
    )
    
    current_page.insert_text(
        fitz.Point(margin_x + 14, y_cursor + 26),
        title,
        fontsize=16,
        fontname="helv",
        color=(0.1, 0.25, 0.55)
    )
    current_page.insert_text(
        fitz.Point(margin_x + 14, y_cursor + 44),
        subtitle,
        fontsize=10,
        fontname="helv",
        color=(0.3, 0.3, 0.3)
    )
    current_page.insert_text(
        fitz.Point(margin_x + 14, y_cursor + 58),
        f"Document ID: {doc_code} | Effective Date: January 1, 2026 | Classification: Internal Use Only",
        fontsize=8,
        fontname="helv",
        color=(0.45, 0.45, 0.45)
    )
    
    y_cursor += 90
    
    # Process sections
    for sec_heading, paragraphs in sections:
        # Check if heading fits on page
        if y_cursor + 70 > (page_height - margin_bottom):
            start_new_page()
            
        # Draw section heading with a colored bar on left
        current_page.draw_rect(
            fitz.Rect(margin_x, y_cursor - 2, margin_x + 4, y_cursor + 14),
            color=None,
            fill=(0.15, 0.45, 0.75)
        )
        current_page.insert_text(
            fitz.Point(margin_x + 10, y_cursor + 11),
            sec_heading,
            fontsize=12,
            fontname="helv",
            color=(0.12, 0.2, 0.35)
        )
        y_cursor += 22
        
        # Draw paragraphs
        for para in paragraphs:
            # Estimate needed height or try placing in remaining space
            rect = fitz.Rect(margin_x, y_cursor, margin_x + content_width, page_height - margin_bottom)
            res = current_page.insert_textbox(
                rect,
                para,
                fontsize=9.5,
                fontname="helv",
                color=(0.15, 0.15, 0.15),
                align=fitz.TEXT_ALIGN_LEFT
            )
            
            # If text didn't fit in the remaining page space (res < 0), move to next page
            if res < 0:
                # Clear and re-insert on next page
                start_new_page()
                rect = fitz.Rect(margin_x, y_cursor, margin_x + content_width, page_height - margin_bottom)
                res = current_page.insert_textbox(
                    rect,
                    para,
                    fontsize=9.5,
                    fontname="helv",
                    color=(0.15, 0.15, 0.15),
                    align=fitz.TEXT_ALIGN_LEFT
                )
                
            used_height = rect.height - res if res >= 0 else 50
            y_cursor += used_height + 10
            
        y_cursor += 10  # Spacing between sections

    # Add footers with page numbering to all pages
    total_pages = len(doc)
    for idx, page in enumerate(doc, start=1):
        page.draw_line(
            fitz.Point(margin_x, page_height - 35),
            fitz.Point(page_width - margin_x, page_height - 35),
            color=(0.8, 0.8, 0.8),
            width=0.8
        )
        page.insert_text(
            fitz.Point(margin_x, page_height - 22),
            "CONFIDENTIAL | TechNova Solutions Internal Knowledge Base",
            fontsize=8,
            fontname="helv",
            color=(0.5, 0.5, 0.5)
        )
        page.insert_text(
            fitz.Point(page_width - margin_x - 65, page_height - 22),
            f"Page {idx} of {total_pages}",
            fontsize=8,
            fontname="helv",
            color=(0.5, 0.5, 0.5)
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    print(f"Generated: {output_path} ({total_pages} pages)")


def build_documents():
    # Resolve target directory
    base_dir = Path(__file__).resolve().parent.parent.parent
    docs_dir = base_dir / "company-docs"
    
    # 1. Employee Handbook
    employee_handbook_sections = [
        (
            "1. Company Overview & Core Values",
            [
                "Welcome to TechNova Solutions. We are an enterprise AI software platform dedicated to empowering global enterprises with autonomous AI agents, intelligent workflow automation, and real-time knowledge retrieval systems.",
                "Our four foundational core values are:\n• Innovation First: We pursue creative problem solving and maintain continuous curiosity.\n• Customer Obsession: We measure our success through the measurable impact delivered to our clients.\n• Radical Transparency: Open communication, psychological safety, and clear accountability.\n• Inclusivity & Diversity: Fostering welcoming environments for teams across all backgrounds."
            ]
        ),
        (
            "2. Employment Terms & Probationary Period",
            [
                "All new full-time team members undergo an initial 90-calendar-day probationary period. During this period, the employee and their direct manager engage in bi-weekly check-ins to review role milestones, culture assimilation, and key objectives.",
                "Formal 45-day and 90-day progress assessments will be conducted. Upon successful completion of the 90th day, the employee transitions to regular permanent employment status with eligibility for discretionary performance bonuses."
            ]
        ),
        (
            "3. Working Hours & Remote Workplace Policy",
            [
                "TechNova operates on a flexible hybrid work structure based on a 40-hour work week. Employees may choose to work remotely up to three (3) days per week, with two (2) days dedicated to in-office collaboration at designated regional hubs.",
                "Core Collaboration Hours are established as 10:00 AM to 3:00 PM Eastern Standard Time (EST). All team members are expected to be reachable via Slack and email during these core hours regardless of their physical work location."
            ]
        ),
        (
            "4. Paid Time Off (PTO), Holidays & Leave Policies",
            [
                "Annual Leave: Full-time employees accrue 20 days of Paid Time Off (PTO) per calendar year, accrued on a pro-rata monthly schedule. A maximum of 5 unused PTO days can be rolled over to the subsequent calendar year.",
                "Sick & Personal Well-Being Leave: 10 dedicated paid days per year for physical illness, mental health recovery, or family medical emergencies. No doctor's certification is required for absences up to three consecutive business days.",
                "Parental Leave: TechNova offers 16 weeks of fully paid parental leave for primary caregivers and 6 weeks of fully paid leave for secondary caregivers. Eligible for birth, adoption, or foster placement following 6 months of continuous service.",
                "Company Holidays: TechNova observes 11 paid official holidays annually, including New Year's Day, Memorial Day, Juneteenth, Independence Day, Labor Day, Thanksgiving (Thursday & Friday), and Year-End Winter Break (Dec 24 - Jan 1)."
            ]
        ),
        (
            "5. Compensation, Benefits & Financial Well-being",
            [
                "Health & Wellness: TechNova covers 90% of medical, dental, and vision insurance premiums for employees and 75% for eligible dependents. Coverage begins on the first calendar day of the month following employment start.",
                "Retirement 401(k): TechNova provides dollar-for-dollar company 401(k) matching up to 5% of annual salary. All employer contributions vest immediately upon deposit.",
                "Professional Development: Each full-time employee receives an annual $1,500 USD Learning & Development stipend for books, conferences, certifications, and academic courses."
            ]
        ),
        (
            "6. Workplace Conduct & Anti-Harassment",
            [
                "TechNova enforces a strict Zero-Tolerance policy against discrimination, harassment, bullying, or retaliation of any form. Every employee has the right to work in a dignified and supportive setting.",
                "Concerns may be reported confidentially to Human Resources at hr@technova.internal or anonymously through our 24/7 whistleblower hotline at ethics.technova.internal."
            ]
        )
    ]
    
    # 2. IT & Security Policy
    it_security_sections = [
        (
            "1. Scope, Purpose & Authority",
            [
                "This policy applies to all TechNova personnel, contractors, vendors, and third-party affiliates who access company IT assets, corporate networks, software repositories, customer environments, and cloud infrastructure.",
                "Compliance with this policy is mandatory. Failure to observe security protocols may lead to revocation of credentials, disciplinary action, and legal remedies as defined under corporate governance frameworks."
            ]
        ),
        (
            "2. Identity Management & Password Standards",
            [
                "Password Complexity: All passwords must contain a minimum of 14 characters and combine uppercase letters, lowercase letters, numbers, and special symbols (e.g., !@#$%^&*).",
                "Password Lifespan & History: Passwords must be updated every 90 days. The system prevents reuse of the previous six (6) historical passwords.",
                "Multi-Factor Authentication (MFA): MFA is mandatory across all corporate systems, including Google Workspace, GitHub Enterprise, AWS/Azure consoles, and VPN. SMS-based 2FA is prohibited; hardware FIDO2 keys (YubiKey) or time-based authenticator apps (1Password/Okta) are required."
            ]
        ),
        (
            "3. Device Management & Endpoint Protection",
            [
                "Company-Provided Laptops: All corporate laptops run centrally managed MDM (Mobile Device Management) software with BitLocker/FileVault whole-disk encryption enabled and non-bypassable.",
                "Screen Auto-Lock: Operating system display sleep and screen lock are enforced after five (5) minutes of user inactivity.",
                "Clean Desk & Clean Screen: Sensitive paper documents must be locked in designated filing cabinets when unattended. Workstations must be manually locked whenever leaving the desk area."
            ]
        ),
        (
            "4. Remote Access & Corporate VPN",
            [
                "All remote connections to internal TechNova databases, staging servers, and administrative dashboards must route through the WireGuard corporate VPN gateway.",
                "Split-tunneling is strictly disabled on all corporate VPN profiles to prevent unauthorized data exfiltration. Connecting corporate hardware to public unencrypted Wi-Fi networks without an active VPN tunnel is strictly forbidden."
            ]
        ),
        (
            "5. Data Classification & Protection Framework",
            [
                "TechNova categorizes data into four distinct tiers:\n• Public: Marketing materials, published documentation, public blog posts.\n• Internal: General correspondence, engineering notes, internal wikis.\n• Confidential: Financial forecasts, commercial contracts, source code.\n• Restricted: Personally Identifiable Information (PII), customer credentials, encryption keys, and payment card details.",
                "All Restricted data must be encrypted both in transit (TLS 1.3) and at rest using AES-256-GCM. Access is strictly granted based on Least Privilege and Role-Based Access Control (RBAC)."
            ]
        ),
        (
            "6. Security Incident Response & Reporting",
            [
                "Any suspected security breach, phishing email, stolen laptop, or accidental credential leak must be reported within one (1) hour of discovery.",
                "Reporting Channels:\n• Emergency Hotline: Extension 4499 (Internal VoIP)\n• Incident Email: security-incident@technova.internal\n• Dedicated Slack Channel: #security-ops-urgent",
                "Our Computer Security Incident Response Team (CSIRT) follows the NIST SP 800-61 framework for triage, containment, eradication, and post-incident root cause analysis."
            ]
        )
    ]
    
    # 3. Product Catalog & Pricing
    product_catalog_sections = [
        (
            "1. Product Overview: NovaCloud AI Platform",
            [
                "The NovaCloud AI Platform is TechNova's flagship enterprise Agentic RAG solution. It bridges unstructured enterprise documentation with autonomous multi-agent reasoning, semantic vector search, and transactional API integrations.",
                "Core Architecture Highlights:\n• Hybrid Retrieval Engine: Blends dense semantic vector indexing with BM25 keyword search for superior recall.\n• Autonomous Agent Orchestration: Multi-step reasoning loops powered by ReAct and Plan-and-Solve patterns.\n• Real-Time Knowledge Graph: Maintains relational entity mapping across disparate documentation silos.\n• Enterprise Guardrails: PII redaction, prompt injection defense, and hallucinations mitigation."
            ]
        ),
        (
            "2. Subscription Plans & Pricing Matrix",
            [
                "Tier 1 — Starter ($499 USD per month):\n• Includes up to 10 user seats.\n• Monthly quota: 50,000 query operations and 2,500 document ingestion pages.\n• Service Level Agreement (SLA): 99.5% uptime guarantee.\n• Support: Standard email support with 24-business-hour response time.\n• Deployment: Multi-tenant secure cloud environment.",
                "Tier 2 — Growth ($1,499 USD per month):\n• Includes up to 50 user seats.\n• Monthly quota: 250,000 query operations and 15,000 document ingestion pages.\n• Service Level Agreement (SLA): 99.9% uptime guarantee.\n• Support: Priority email and Slack support with 4-hour response time.\n• Features: Custom prompt templates, webhook triggers, and role-based permissions.",
                "Tier 3 — Enterprise ($4,999 USD per month):\n• Unlimited user seats.\n• Monthly quota: 2,000,000 query operations and unlimited document ingestion.\n• Service Level Agreement (SLA): 99.99% uptime guarantee.\n• Support: 24/7/365 dedicated Technical Account Manager (TAM) and 1-hour critical response SLA.\n• Deployment: Dedicated Single-Tenant VPC, on-premise air-gapped container deployment, and custom LLM fine-tuning."
            ]
        ),
        (
            "3. Add-On Enterprise Modules",
            [
                "• NovaVector Scale Unit: $300/mo per additional 1,000,000 indexed vector embeddings.\n• Compliance & Audit Vault: $500/mo for SOC2 Type II, HIPAA, and GDPR automated audit trails and immutable tamper-evident logs.\n• Multi-Region Active-Active Replication: $1,200/mo providing sub-50ms global latency and automated failover."
            ]
        ),
        (
            "4. Service Level Agreement (SLA) & Penalty Credits",
            [
                "TechNova stands firmly behind service availability for Enterprise customers with the following service credit schedule:\n• 99.9% to 99.98% Uptime: 10% credit applied to next monthly invoice.\n• 99.0% to 99.89% Uptime: 25% credit applied to next monthly invoice.\n• Below 99.0% Uptime: 50% credit applied to next monthly invoice plus root cause post-mortem within 48 hours."
            ]
        ),
        (
            "5. Licensing, Billing & Contract Terms",
            [
                "Invoicing Options: Subscriptions are billed on an annual commitment basis with quarterly or upfront annual payments. Customers paying annually in advance receive a 15% discount.",
                "Renewal & Cancellation: Agreements renew automatically for 12-month periods unless written notice of non-renewal is provided at least thirty (30) days prior to the expiration date."
            ]
        )
    ]
    
    # Generate the 3 documents
    create_pdf(
        docs_dir / "employee_handbook.pdf",
        "Employee Handbook & Workplace Policies",
        "Human Resources & Organizational Guidelines",
        "POL-HR-2026",
        employee_handbook_sections
    )
    
    create_pdf(
        docs_dir / "it_security_policy.pdf",
        "IT Security & Data Protection Policy",
        "Information Security Standards & Compliance Procedures",
        "POL-SEC-2026",
        it_security_sections
    )
    
    create_pdf(
        docs_dir / "product_catalog_and_pricing.pdf",
        "Enterprise Product Catalog & SLA Guidelines",
        "Commercial Tiers, Technical Specifications & Guarantees",
        "DOC-CAT-2026",
        product_catalog_sections
    )
    
    print("\nAll 3 sample company PDFs generated successfully!")


if __name__ == "__main__":
    build_documents()

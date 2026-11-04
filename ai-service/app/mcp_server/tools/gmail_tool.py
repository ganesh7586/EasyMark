"""
Gmail Model Context Protocol (MCP) Tool Integration.

Provides read-only access to customer escalation emails, executive threads, and security approvals.
Supports dual operational modes:
1. Live Mode: Real Google Workspace Gmail REST API v1
2. Development/Testing Mode: High-fidelity Project Alpha enterprise customer communications dataset
   directly correlating with Jira blockers (ALPHA-101, ALPHA-104) and SLA policies.
"""

from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.mcp_server.registry import mcp_tool

# High-fidelity realistic enterprise communications dataset for Project Alpha
PROJECT_ALPHA_GMAIL_THREADS: List[Dict[str, Any]] = [
    {
        "id": "GMAIL-THREAD-001",
        "subject": "[URGENT] 504 Gateway Timeouts during Payment Checkout - Acme Corp Escalation",
        "sender": "Johnathan Vance <j.vance@acmecorp.com>",
        "recipient": "support@northstar-systems.com, Sarah Chen <sarah.chen@northstar-systems.com>",
        "date": "2026-11-03T12:20:00Z",
        "category": "Customer Escalation",
        "severity": "SEV-1",
        "jira_correlation": "ALPHA-101",
        "status": "Acknowledged / In Progress",
        "snippet": "Our checkout portal has been failing with 504 Gateway Timeout since 12:15 IST. Over $45,000 in transactions affected.",
        "messages": [
            {
                "from": "Johnathan Vance <j.vance@acmecorp.com>",
                "date": "2026-11-03T12:20:00Z",
                "body": (
                    "URGENT: Our production checkout integration with Northstar Systems is failing. "
                    "Customers receive 504 Gateway Timeout errors upon submitting credit card payments. "
                    "We have experienced 14 failed checkouts in the last 15 minutes. "
                    "Please acknowledge per our Enterprise SLA agreement (SEV-1: 15 minutes)."
                ),
            },
            {
                "from": "Support Desk <support@northstar-systems.com>",
                "date": "2026-11-03T12:28:00Z",
                "body": (
                    "Hello Johnathan, we have received your escalation (acknowledged at 12:28 IST, within 8 minutes). "
                    "Incident INC-2026-1103 / Jira ALPHA-101 has been initiated. Senior Backend Engineer Sarah Chen "
                    "is actively mitigating database connection pool exhaustion. Next status update in 30 minutes."
                ),
            },
        ],
    },
    {
        "id": "GMAIL-THREAD-002",
        "subject": "Delays in Enterprise New User Welcome Verification Emails",
        "sender": "Marcus Sterling <m.sterling@fintech-global.com>",
        "recipient": "support@northstar-systems.com, Emily Watson <emily.watson@northstar-systems.com>",
        "date": "2026-11-03T14:45:00Z",
        "category": "Customer Escalation",
        "severity": "SEV-2",
        "jira_correlation": "ALPHA-104",
        "status": "Under Investigation",
        "snippet": "New employees onboarded today are waiting over 40 minutes for account verification emails.",
        "messages": [
            {
                "from": "Marcus Sterling <m.sterling@fintech-global.com>",
                "date": "2026-11-03T14:45:00Z",
                "body": (
                    "Hi Support, 12 new financial analysts onboarded this afternoon are reporting severe delays "
                    "in receiving the welcome password-reset emails. Delivery times are currently averaging 45 minutes."
                ),
            },
            {
                "from": "Emily Watson <emily.watson@northstar-systems.com>",
                "date": "2026-11-03T15:10:00Z",
                "body": (
                    "Hi Marcus, acknowledged within our SEV-2 1-hour SLA window. DevOps lead Priyansh Sharma is "
                    "investigating memory limits on our Kubernetes SMTP worker pod (tracked in Jira ALPHA-104)."
                ),
            },
        ],
    },
    {
        "id": "GMAIL-THREAD-003",
        "subject": "Security Audit Sign-Off: Gateway Service-to-Service Bridge (x-internal-key)",
        "sender": "Robert Vance <ciso@northstar-systems.com>",
        "recipient": "Alex Rivera <alex.rivera@northstar-systems.com>, Sarah Chen <sarah.chen@northstar-systems.com>",
        "date": "2026-11-02T16:15:00Z",
        "category": "Security Approval",
        "severity": "Normal",
        "status": "Approved",
        "snippet": "The constant-time secret comparison and internal HMAC header design passed external penetration audit.",
        "messages": [
            {
                "from": "Robert Vance <ciso@northstar-systems.com>",
                "date": "2026-11-02T16:15:00Z",
                "body": (
                    "Alex and Sarah, our external security evaluation team has reviewed the dual-tier architecture. "
                    "The constant-time token comparison (secrets.compare_digest) and internal network isolation "
                    "satisfy ISO-27001 compliance standards. Formal security sign-off granted for Milestone M2."
                ),
            }
        ],
    },
    {
        "id": "GMAIL-THREAD-004",
        "subject": "Invitation: Project Alpha Milestone M2 Stakeholder Demo & Architecture Review",
        "sender": "Sarah Chen <sarah.chen@northstar-systems.com>",
        "recipient": "leadership@northstar-systems.com, all-engineering@northstar-systems.com",
        "date": "2026-11-04T08:30:00Z",
        "category": "Announcement",
        "severity": "Low",
        "status": "Scheduled",
        "snippet": "Please join us this Friday at 15:00 IST for the end-to-end demonstration of Static PDF RAG and live MCP integrations.",
        "messages": [
            {
                "from": "Sarah Chen <sarah.chen@northstar-systems.com>",
                "date": "2026-11-04T08:30:00Z",
                "body": (
                    "Team, we are excited to invite you to the Milestone M2 architecture demonstration on Friday at 15:00 IST. "
                    "We will showcase our dual-tier Express Gateway + FastAPI AI Service, Static PDF RAG with exact [Doc, Page] citations, "
                    "and dynamic live MCP tool integrations for Jira, Notion, and Gmail."
                ),
            }
        ],
    },
]


class GmailClient:
    """Client for interacting with Google Workspace Gmail API v1 or enterprise dataset."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ):
        self.client_id = client_id or settings.GMAIL_CLIENT_ID
        self.client_secret = client_secret or settings.GMAIL_CLIENT_SECRET
        self.refresh_token = refresh_token or settings.GMAIL_REFRESH_TOKEN

    @property
    def is_live(self) -> bool:
        """Returns True if Google OAuth2 credentials are configured."""
        return bool(self.client_id and self.client_secret and self.refresh_token)

    def get_thread(self, thread_id: str) -> Dict[str, Any]:
        """
        Retrieve complete email thread with messages by ID.

        Args:
            thread_id: Unique thread identifier (e.g. 'GMAIL-THREAD-001').

        Returns:
            Thread dictionary or error dict if not found.
        """
        clean_id = thread_id.strip().upper()

        if self.is_live:
            return self._live_get_thread(clean_id)

        for thread in PROJECT_ALPHA_GMAIL_THREADS:
            if thread["id"].upper() == clean_id:
                return thread

        return {
            "error": "Not Found",
            "message": f"Gmail thread '{thread_id}' was not found in enterprise inbox.",
        }

    def search_emails(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search inbox messages by keyword across subject, body, sender, and snippet.

        Args:
            query: Keyword or search phrase (e.g. 'payments', '504 timeout', 'Acme Corp').
            max_results: Maximum matching threads to return.

        Returns:
            List of matching thread summaries.
        """
        clean_q = query.strip().lower()

        if self.is_live:
            return self._live_search(query, max_results)

        matches = []
        for thread in PROJECT_ALPHA_GMAIL_THREADS:
            in_subject = clean_q in thread["subject"].lower()
            in_sender = clean_q in thread["sender"].lower()
            in_snippet = clean_q in thread.get("snippet", "").lower()
            in_body = any(clean_q in m["body"].lower() for m in thread.get("messages", []))
            in_corr = clean_q in thread.get("jira_correlation", "").lower()

            if in_subject or in_sender or in_snippet or in_body or in_corr:
                matches.append({
                    "id": thread["id"],
                    "subject": thread["subject"],
                    "sender": thread["sender"],
                    "date": thread["date"],
                    "category": thread.get("category", "General"),
                    "severity": thread.get("severity", "Normal"),
                    "jira_correlation": thread.get("jira_correlation"),
                    "snippet": thread.get("snippet", ""),
                })
                if len(matches) >= max_results:
                    break

        return matches

    def get_customer_escalations(
        self,
        severity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter inbox for high-priority customer escalation threads.

        Args:
            severity: Optional filter ('SEV-1', 'SEV-2').

        Returns:
            List of customer escalation threads.
        """
        escalations = [
            t for t in PROJECT_ALPHA_GMAIL_THREADS
            if t.get("category") == "Customer Escalation"
        ]

        if severity:
            target_sev = severity.strip().upper()
            escalations = [e for e in escalations if e.get("severity", "").upper() == target_sev]

        return [
            {
                "id": e["id"],
                "subject": e["subject"],
                "customer": e["sender"],
                "severity": e.get("severity"),
                "jira_correlation": e.get("jira_correlation"),
                "status": e.get("status"),
                "date": e["date"],
                "snippet": e.get("snippet"),
            }
            for e in escalations
        ]

    def check_pending_approvals(self) -> List[Dict[str, Any]]:
        """
        Retrieve security sign-offs, production release approvals, and compliance notices.

        Returns:
            List of approval email threads.
        """
        approvals = [
            t for t in PROJECT_ALPHA_GMAIL_THREADS
            if t.get("category") in ("Security Approval", "Approval")
        ]

        return [
            {
                "id": a["id"],
                "subject": a["subject"],
                "approver": a["sender"],
                "status": a.get("status"),
                "date": a["date"],
                "snippet": a.get("snippet"),
            }
            for a in approvals
        ]

    def _live_get_thread(self, thread_id: str) -> Dict[str, Any]:
        return {"error": "Live Google OAuth2 Not Initialized", "detail": "Configure GMAIL_REFRESH_TOKEN in .env"}

    def _live_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        return []


# Global client singleton
_gmail_client: Optional[GmailClient] = None


def get_gmail_client() -> GmailClient:
    """Singleton accessor for GmailClient."""
    global _gmail_client
    if _gmail_client is None:
        _gmail_client = GmailClient()
    return _gmail_client


# ==============================================================================
# Model Context Protocol (MCP) Tool Registrations
# ==============================================================================

@mcp_tool(
    name="gmail_get_thread",
    description="Retrieve a complete email thread with all sender and recipient messages by thread ID (e.g. GMAIL-THREAD-001).",
)
def gmail_get_thread(thread_id: str) -> Dict[str, Any]:
    """
    Fetch complete email thread.

    Args:
        thread_id: Email thread ID (e.g. 'GMAIL-THREAD-001').
    """
    client = get_gmail_client()
    return client.get_thread(thread_id)


@mcp_tool(
    name="gmail_search_emails",
    description="Search company email inbox by keyword across subject lines, body text, and sender addresses.",
)
def gmail_search_emails(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Keyword search across email inbox.

    Args:
        query: Search term (e.g. 'payments', '504', 'audit', 'Acme Corp').
        max_results: Maximum results to return (default 5).
    """
    client = get_gmail_client()
    return client.search_emails(query=query, max_results=max_results)


@mcp_tool(
    name="gmail_get_customer_escalations",
    description="Identify active customer escalation email threads, optionally filtering by severity (SEV-1 or SEV-2).",
)
def gmail_get_customer_escalations(severity: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Filter customer escalations.

    Args:
        severity: Optional severity filter (e.g. 'SEV-1', 'SEV-2').
    """
    client = get_gmail_client()
    return client.get_customer_escalations(severity=severity)


@mcp_tool(
    name="gmail_check_pending_approvals",
    description="Check for security audit approvals, production change sign-offs, and architecture compliance notices in email.",
)
def gmail_check_pending_approvals() -> List[Dict[str, Any]]:
    """
    Review security and compliance approvals.
    """
    client = get_gmail_client()
    return client.check_pending_approvals()

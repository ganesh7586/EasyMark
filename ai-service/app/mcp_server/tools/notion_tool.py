"""
Notion Model Context Protocol (MCP) Tool Integration.

Provides read-only access to Notion workspace documentation, meeting notes, PRDs, and action items.
Supports dual operational modes:
1. Live Mode: Real Notion API v1 (via NOTION_API_KEY + NOTION_DATABASE_ID)
2. Development/Testing Mode: High-fidelity Project Alpha enterprise dataset directly matching
   the company SLA and project charter policies.
"""

from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.mcp_server.registry import mcp_tool

# High-fidelity realistic enterprise documentation dataset for Project Alpha
PROJECT_ALPHA_NOTION_PAGES: List[Dict[str, Any]] = [
    {
        "id": "NOTION-SPEC-01",
        "title": "Project Alpha - Sprint 4 Technical Architecture & Milestone M2 Spec",
        "category": "Architecture Spec",
        "author": "Sarah Chen",
        "author_role": "Senior Backend Engineer",
        "last_edited": "2026-11-03T16:45:00Z",
        "tags": ["architecture", "spec", "milestone-m2", "database"],
        "summary": "Technical blueprint detailing microservice boundaries, MongoDB vector search, and connection pool sizing.",
        "content": (
            "# Project Alpha - Sprint 4 Architecture\n\n"
            "## 1. System Topology\n"
            "Project Alpha decomposes our legacy system into a dual-tier architecture:\n"
            "- Node.js Express Gateway (Port 5000): Handles client auth, rate limiting, and request forwarding.\n"
            "- Python FastAPI AI Service (Port 8000): Orchestrates RAG, LangGraph agent workflows, and MCP tools.\n\n"
            "## 2. Database Connection Pooling Guidelines\n"
            "All database drivers (PyMongo) must configure:\n"
            "- minPoolSize: 5, maxPoolSize: 50\n"
            "- serverSelectionTimeoutMS: 2000ms\n"
            "Failure to release unclosed cursors exhausts the pool and triggers 504 timeouts (ref: ALPHA-101).\n\n"
            "## 3. Security Bridge\n"
            "Inter-service calls require the 'x-internal-key' header validated via constant-time comparison."
        ),
    },
    {
        "id": "NOTION-NOTE-02",
        "title": "Meeting Notes: Weekly Engineering Sync (2026-11-03)",
        "category": "Meeting Notes",
        "author": "Sarah Chen",
        "author_role": "Senior Backend Engineer",
        "date": "2026-11-03",
        "last_edited": "2026-11-03T18:30:00Z",
        "attendees": ["Sarah Chen", "Alex Rivera", "David Kim", "Priyansh Sharma", "Maya Lin"],
        "tags": ["sync", "meeting-notes", "weekly"],
        "summary": "Engineering sync discussing SEV-1 payments blocker, security bridge signoff, and chat UI citations.",
        "content": (
            "# Weekly Engineering Sync — Nov 3, 2026\n\n"
            "## Agenda & Discussion:\n"
            "1. **Production Blockers:** SEV-1 ticket ALPHA-101 opened for payments database timeouts. "
            "Sarah Chen identified leaked connections in receipt generator; patch targeted for deployment today.\n"
            "2. **Security Bridge:** Alex Rivera confirmed Express to FastAPI x-internal-key bridge is passing tests.\n"
            "3. **Milestone M2 Target:** Executive demo scheduled for end of week.\n\n"
            "## Action Items:\n"
            "- [x] Alex Rivera: Finalize internal API key rotation policy document.\n"
            "- [ ] Sarah Chen: Deploy database connection pool fix for ALPHA-101.\n"
            "- [ ] Priyansh Sharma: Profile Kubernetes SMTP worker memory to resolve ALPHA-104 email delays.\n"
            "- [ ] Maya Lin: Connect React citation pills to the policy preview side drawer."
        ),
        "action_items": [
            {"task": "Finalize internal API key rotation policy document", "assignee": "Alex Rivera", "status": "Completed"},
            {"task": "Deploy database connection pool fix for ALPHA-101", "assignee": "Sarah Chen", "status": "Pending"},
            {"task": "Profile Kubernetes SMTP worker memory to resolve ALPHA-104 email delays", "assignee": "Priyansh Sharma", "status": "Pending"},
            {"task": "Connect React citation pills to the policy preview side drawer", "assignee": "Maya Lin", "status": "Pending"},
        ],
    },
    {
        "id": "NOTION-PRD-03",
        "title": "Product Requirements Document (PRD): Assistant Citation Badges & Provenance",
        "category": "PRD",
        "author": "Emily Watson",
        "author_role": "Customer Success Lead",
        "last_edited": "2026-11-02T11:20:00Z",
        "tags": ["prd", "citations", "ux", "frontend"],
        "summary": "Product requirements for trustworthy AI policy answers with exact document and page citations.",
        "content": (
            "# PRD: Grounded Citations & Evidence Provenance\n\n"
            "## Problem Statement:\n"
            "Employees need absolute confidence that the AI assistant's answers are verified policy facts rather than hallucinations.\n\n"
            "## Functional Requirements:\n"
            "1. **Exact Page Provenance:** Every statement derived from company PDFs must attach [Document_Name.pdf, Page X].\n"
            "2. **Clickable UI Pills:** In the React frontend, citations render as interactive badges.\n"
            "3. **Zero Speculation:** If policy docs do not contain facts to answer the query, state: "
            "'The available company policy documents do not contain sufficient information to answer this question.'"
        ),
    },
    {
        "id": "NOTION-POST-04",
        "title": "Incident Post-Mortem Draft: SEV-1 Database Pool Exhaustion",
        "category": "Post-Mortem",
        "author": "Priyansh Sharma",
        "author_role": "DevOps Lead",
        "date": "2026-11-03",
        "last_edited": "2026-11-04T08:15:00Z",
        "tags": ["incident", "sev-1", "post-mortem", "payments"],
        "summary": "Draft post-mortem analyzing root cause, response metrics, and preventive remediation for ALPHA-101.",
        "content": (
            "# Incident Post-Mortem — SEV-1 Database Pool Exhaustion\n\n"
            "## Incident Overview:\n"
            "- Incident ID: INC-2026-1103\n"
            "- Severity: SEV-1 (Critical Business Impact)\n"
            "- Affected Service: Payments API\n"
            "- Time to Acknowledge: 8 minutes (SLA Target: 15 minutes — MET)\n"
            "- Time to Resolution: Ongoing mitigation under ALPHA-101\n\n"
            "## Root Cause:\n"
            "Peak lunch traffic coincided with asynchronous receipt generation jobs holding open unpooled connections.\n\n"
            "## Preventative Actions:\n"
            "- Wrap MongoDB operations in explicit session context managers.\n"
            "- Add Prometheus connection gauge alert at 80% pool utilization."
        ),
        "action_items": [
            {"task": "Wrap MongoDB operations in explicit session context managers", "assignee": "Sarah Chen", "status": "Pending"},
            {"task": "Add Prometheus connection gauge alert at 80% pool utilization", "assignee": "Priyansh Sharma", "status": "Pending"},
        ],
    },
]


class NotionClient:
    """Client for interacting with Notion API v1 or enterprise documentation dataset."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        database_id: Optional[str] = None,
    ):
        self.api_key = api_key or settings.NOTION_API_KEY
        self.database_id = database_id or settings.NOTION_DATABASE_ID

    @property
    def is_live(self) -> bool:
        """Returns True if live Notion API credentials are configured."""
        return bool(self.api_key)

    def get_page(self, page_id_or_title: str) -> Dict[str, Any]:
        """
        Retrieve a Notion page by its ID or title.

        Args:
            page_id_or_title: Unique Notion page ID (e.g. 'NOTION-SPEC-01') or title substring.

        Returns:
            Page dictionary or error dict if not found.
        """
        clean_target = page_id_or_title.strip().lower()

        if self.is_live:
            return self._live_get_page(page_id_or_title)

        for page in PROJECT_ALPHA_NOTION_PAGES:
            if page["id"].lower() == clean_target or clean_target in page["title"].lower():
                return page

        return {
            "error": "Not Found",
            "message": f"Notion page matching '{page_id_or_title}' was not found in workspace.",
        }

    def search_pages(self, query: str) -> List[Dict[str, Any]]:
        """
        Search Notion workspace pages by keyword across title, summary, content, and tags.

        Args:
            query: Keyword or phrase to search (e.g. 'connection pool', 'citations', 'SEV-1').

        Returns:
            List of matching page summaries.
        """
        clean_q = query.strip().lower()

        if self.is_live:
            return self._live_search(query)

        matches = []
        for page in PROJECT_ALPHA_NOTION_PAGES:
            in_title = clean_q in page["title"].lower()
            in_summary = clean_q in page.get("summary", "").lower()
            in_content = clean_q in page.get("content", "").lower()
            in_tags = any(clean_q in t.lower() for t in page.get("tags", []))

            if in_title or in_summary or in_content or in_tags:
                matches.append({
                    "id": page["id"],
                    "title": page["title"],
                    "category": page.get("category", "General"),
                    "author": page.get("author", "Unknown"),
                    "last_edited": page.get("last_edited", ""),
                    "tags": page.get("tags", []),
                    "summary": page.get("summary", ""),
                })

        return matches

    def get_meeting_notes(self, date_or_tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve meeting notes, optionally filtered by date (YYYY-MM-DD) or tag.

        Args:
            date_or_tag: Optional date or tag filter.

        Returns:
            List of meeting note pages.
        """
        notes = [p for p in PROJECT_ALPHA_NOTION_PAGES if p.get("category") == "Meeting Notes"]

        if date_or_tag:
            target = date_or_tag.strip().lower()
            filtered = []
            for note in notes:
                match_date = note.get("date") == target
                match_tag = any(target in t.lower() for t in note.get("tags", []))
                if match_date or match_tag:
                    filtered.append(note)
            return filtered

        return notes

    def get_action_items(self, assignee: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Collect action items extracted from meeting notes and post-mortems.

        Args:
            assignee: Optional filter by assigned engineer name (e.g. 'Sarah Chen').

        Returns:
            List of action items with source page title and status.
        """
        items: List[Dict[str, Any]] = []

        for page in PROJECT_ALPHA_NOTION_PAGES:
            page_action_items = page.get("action_items", [])
            for item in page_action_items:
                record = {
                    "source_page_id": page["id"],
                    "source_title": page["title"],
                    "task": item["task"],
                    "assignee": item["assignee"],
                    "status": item["status"],
                }
                if assignee:
                    if assignee.strip().lower() in item["assignee"].lower():
                        items.append(record)
                else:
                    items.append(record)

        return items

    def _live_get_page(self, page_id: str) -> Dict[str, Any]:
        url = f"https://api.notion.com/v1/pages/{page_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    return resp.json()
                return {"error": resp.status_code, "message": resp.text}
        except Exception as err:
            return {"error": "Live Notion API Connection Failed", "detail": str(err)}

    def _live_search(self, query: str) -> List[Dict[str, Any]]:
        url = "https://api.notion.com/v1/search"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, headers=headers, json={"query": query})
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data.get("results", []):
                        props = item.get("properties", {})
                        title = ""
                        for val in props.values():
                            if val.get("type") == "title" and val.get("title"):
                                title = val["title"][0].get("plain_text", "")
                                break
                        results.append({
                            "id": item.get("id"),
                            "title": title or "Untitled Page",
                            "last_edited": item.get("last_edited_time"),
                        })
                    return results
                return []
        except Exception:
            return []


# Global client singleton
_notion_client: Optional[NotionClient] = None


def get_notion_client() -> NotionClient:
    """Singleton accessor for NotionClient."""
    global _notion_client
    if _notion_client is None:
        _notion_client = NotionClient()
    return _notion_client


# ==============================================================================
# Model Context Protocol (MCP) Tool Registrations
# ==============================================================================

@mcp_tool(
    name="notion_get_page",
    description="Retrieve a complete Notion page document by its ID (e.g. NOTION-SPEC-01) or title, including full markdown content.",
)
def notion_get_page(page_id_or_title: str) -> Dict[str, Any]:
    """
    Fetch Notion page by ID or title.

    Args:
        page_id_or_title: Page ID (e.g. 'NOTION-SPEC-01') or title substring.
    """
    client = get_notion_client()
    return client.get_page(page_id_or_title)


@mcp_tool(
    name="notion_search_pages",
    description="Search Notion workspace documentation and architecture specs by keyword across titles, content, and tags.",
)
def notion_search_pages(query: str) -> List[Dict[str, Any]]:
    """
    Keyword search across workspace documentation.

    Args:
        query: Search term (e.g. 'connection pool', 'citations', 'SEV-1').
    """
    client = get_notion_client()
    return client.search_pages(query)


@mcp_tool(
    name="notion_get_meeting_notes",
    description="Retrieve team meeting notes and engineering sync summaries with optional filtering by date (YYYY-MM-DD) or topic tag.",
)
def notion_get_meeting_notes(date_or_tag: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch meeting notes.

    Args:
        date_or_tag: Optional date (YYYY-MM-DD) or tag filter.
    """
    client = get_notion_client()
    return client.get_meeting_notes(date_or_tag)


@mcp_tool(
    name="notion_get_action_items",
    description="Collect pending and completed action items from meeting notes and incident post-mortems, filtered by assignee.",
)
def notion_get_action_items(assignee: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Collect action items.

    Args:
        assignee: Optional engineer name filter (e.g. 'Sarah Chen', 'Maya Lin').
    """
    client = get_notion_client()
    return client.get_action_items(assignee)

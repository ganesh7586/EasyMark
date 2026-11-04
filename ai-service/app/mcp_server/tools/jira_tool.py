"""
Jira Model Context Protocol (MCP) Tool Integration.

Provides read-only access to Jira Cloud issues, sprint tasks, and blockers.
Supports dual operational modes:
1. Live Mode: Real Atlassian Jira Cloud REST API (via JIRA_BASE_URL + JIRA_API_TOKEN)
2. Development/Testing Mode: High-fidelity Project Alpha enterprise dataset directly matching
   the company SLA and project charter policies.
"""

from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.mcp_server.registry import mcp_tool

# High-fidelity realistic enterprise dataset for Project Alpha
PROJECT_ALPHA_ISSUES: List[Dict[str, Any]] = [
    {
        "key": "ALPHA-101",
        "project": "ALPHA",
        "summary": "[SEV-1] Production Database Connection Pool Exhaustion on Payments API",
        "issue_type": "Bug",
        "priority": "Highest",
        "status": "Blocked",
        "assignee": "Sarah Chen",
        "assignee_role": "Senior Backend Engineer",
        "reporter": "Priyansh Sharma",
        "sprint": "Sprint 4 - Milestone M2",
        "story_points": 5,
        "labels": ["payments", "sev-1", "blocker", "database"],
        "description": (
            "During 12:00-14:00 peak traffic, the Payments API encounters MaxConnectionsError, "
            "leading to 504 gateway timeouts on customer checkout. Active SEV-1 incident requiring "
            "15-minute acknowledgement and 30-minute status updates per Engineering SLA policy."
        ),
        "created": "2026-11-03T08:30:00Z",
        "updated": "2026-11-04T09:15:00Z",
    },
    {
        "key": "ALPHA-102",
        "project": "ALPHA",
        "summary": "Implement HMAC Security Bridge for internal Gateway requests",
        "issue_type": "Story",
        "priority": "High",
        "status": "In Progress",
        "assignee": "Alex Rivera",
        "assignee_role": "Staff Security Engineer",
        "reporter": "Sarah Chen",
        "sprint": "Sprint 4 - Milestone M2",
        "story_points": 8,
        "labels": ["security", "gateway", "backend"],
        "description": (
            "Dual-tier security validation using x-internal-key header with constant-time comparison "
            "(secrets.compare_digest) to prevent side-channel timing attacks."
        ),
        "created": "2026-11-01T10:00:00Z",
        "updated": "2026-11-03T16:20:00Z",
    },
    {
        "key": "ALPHA-103",
        "project": "ALPHA",
        "summary": "Deploy MongoDB Atlas Vector Search Index on document_chunks",
        "issue_type": "Task",
        "priority": "Medium",
        "status": "Done",
        "assignee": "David Kim",
        "assignee_role": "Data Platform Engineer",
        "reporter": "Sarah Chen",
        "sprint": "Sprint 4 - Milestone M2",
        "story_points": 3,
        "labels": ["mongodb", "vector-search", "rag"],
        "description": (
            "Created vector_index on the document_chunks collection in company_intelligence database "
            "with 384 dimensions and cosine similarity metric."
        ),
        "created": "2026-10-30T11:00:00Z",
        "updated": "2026-11-02T14:00:00Z",
    },
    {
        "key": "ALPHA-104",
        "project": "ALPHA",
        "summary": "[SEV-2] Delayed customer onboarding email verification triggers",
        "issue_type": "Bug",
        "priority": "High",
        "status": "Blocked",
        "assignee": "Priyansh Sharma",
        "assignee_role": "DevOps Lead",
        "reporter": "Emily Watson",
        "sprint": "Sprint 4 - Milestone M2",
        "story_points": 3,
        "labels": ["email", "smtp", "sev-2", "blocker"],
        "description": (
            "SMTP queue worker in Kubernetes pod is experiencing memory pressure, delaying "
            "welcome emails by up to 45 minutes. Requires 1-hour acknowledgement per SLA."
        ),
        "created": "2026-11-03T14:10:00Z",
        "updated": "2026-11-04T08:45:00Z",
    },
    {
        "key": "ALPHA-105",
        "project": "ALPHA",
        "summary": "Build Interactive Citations Drawer in React Chat UI",
        "issue_type": "Story",
        "priority": "Medium",
        "status": "In Progress",
        "assignee": "Maya Lin",
        "assignee_role": "Frontend Lead",
        "reporter": "Sarah Chen",
        "sprint": "Sprint 4 - Milestone M2",
        "story_points": 5,
        "labels": ["frontend", "react", "ui"],
        "description": (
            "Add clickable [Document, Page] citation pill badges to chat messages for instant "
            "side-drawer policy passage previews."
        ),
        "created": "2026-11-02T09:30:00Z",
        "updated": "2026-11-03T18:00:00Z",
    },
    {
        "key": "ALPHA-106",
        "project": "ALPHA",
        "summary": "Milestone M2 stakeholder demo preparation and documentation",
        "issue_type": "Task",
        "priority": "Low",
        "status": "To Do",
        "assignee": "Sarah Chen",
        "assignee_role": "Senior Backend Engineer",
        "reporter": "Sarah Chen",
        "sprint": "Sprint 4 - Milestone M2",
        "story_points": 2,
        "labels": ["documentation", "demo", "milestone-m2"],
        "description": (
            "Prepare end-to-end demonstration of static policy RAG and live MCP integrations "
            "for executive review."
        ),
        "created": "2026-11-04T09:00:00Z",
        "updated": "2026-11-04T09:00:00Z",
    },
]


class JiraClient:
    """Client for interacting with Atlassian Jira Cloud or enterprise fallback dataset."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
        default_project: Optional[str] = None,
    ):
        self.base_url = (base_url or settings.JIRA_BASE_URL or "").rstrip("/")
        self.email = email or settings.JIRA_EMAIL
        self.api_token = api_token or settings.JIRA_API_TOKEN
        self.default_project = default_project or settings.JIRA_PROJECT_KEY or "ALPHA"

    @property
    def is_live(self) -> bool:
        """Returns True if valid live Jira Cloud credentials are configured."""
        return bool(self.base_url and self.email and self.api_token)

    def get_sprint_issues(
        self,
        project_key: Optional[str] = None,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve sprint issues filtered by project, status, or assignee.

        Args:
            project_key: Project identifier (defaults to ALPHA).
            status: Optional status filter (e.g., 'Blocked', 'In Progress', 'Done', 'To Do').
            assignee: Optional case-insensitive assignee name filter.

        Returns:
            List of matching Jira issues.
        """
        proj = (project_key or self.default_project).upper()

        if self.is_live:
            return self._live_get_sprint_issues(proj, status, assignee)

        # Dataset mode
        results = [issue for issue in PROJECT_ALPHA_ISSUES if issue["project"] == proj]

        if status:
            target_status = status.strip().lower()
            results = [i for i in results if i["status"].lower() == target_status]

        if assignee:
            target_assignee = assignee.strip().lower()
            results = [i for i in results if target_assignee in i["assignee"].lower()]

        return results

    def get_blockers(self, project_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve all high-severity blocker tickets (status='Blocked' or SEV-1/SEV-2 labels).

        Args:
            project_key: Project identifier (defaults to ALPHA).

        Returns:
            List of blocker issues.
        """
        proj = (project_key or self.default_project).upper()

        if self.is_live:
            jql = f"project = {proj} AND (status = 'Blocked' OR priority in ('Highest', 'Critical') OR labels in ('blocker', 'sev-1', 'sev-2'))"
            return self._live_search(jql)

        return [
            i for i in PROJECT_ALPHA_ISSUES
            if i["project"] == proj and (
                i["status"] == "Blocked"
                or i["priority"] in ("Highest", "Critical")
                or "blocker" in i["labels"]
                or "sev-1" in i["labels"]
            )
        ]

    def get_issue_details(self, issue_key: str) -> Dict[str, Any]:
        """
        Retrieve complete metadata for a specific issue key.

        Args:
            issue_key: Issue key (e.g., 'ALPHA-101').

        Returns:
            Detailed issue dictionary, or error dict if not found.
        """
        clean_key = issue_key.strip().upper()

        if self.is_live:
            return self._live_get_issue(clean_key)

        for issue in PROJECT_ALPHA_ISSUES:
            if issue["key"] == clean_key:
                return issue

        return {
            "error": "Not Found",
            "message": f"Issue '{clean_key}' was not found in Jira project '{self.default_project}'.",
        }

    def search_issues(
        self,
        query: str,
        project_key: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search issues by keyword across summary, description, and labels.

        Args:
            query: Search string or keyword (e.g. 'payments', 'database', 'SEV-1').
            project_key: Optional project scope (defaults to ALPHA).

        Returns:
            List of matching issues.
        """
        proj = (project_key or self.default_project).upper()
        clean_q = query.strip().lower()

        if self.is_live:
            jql = f'project = {proj} AND (text ~ "{query}" OR summary ~ "{query}")'
            return self._live_search(jql)

        matches = []
        for issue in PROJECT_ALPHA_ISSUES:
            if issue["project"] != proj:
                continue

            in_summary = clean_q in issue["summary"].lower()
            in_desc = clean_q in issue["description"].lower()
            in_key = clean_q in issue["key"].lower()
            in_labels = any(clean_q in lbl.lower() for lbl in issue["labels"])

            if in_summary or in_desc or in_key or in_labels:
                matches.append(issue)

        return matches

    def _live_get_sprint_issues(self, project: str, status: Optional[str], assignee: Optional[str]) -> List[Dict[str, Any]]:
        jql_parts = [f"project = {project}"]
        if status:
            jql_parts.append(f"status = '{status}'")
        if assignee:
            jql_parts.append(f"assignee = '{assignee}'")
        return self._live_search(" AND ".join(jql_parts))

    def _live_get_issue(self, issue_key: str) -> Dict[str, Any]:
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, auth=(self.email, self.api_token))
                if resp.status_code == 200:
                    data = resp.json()
                    fields = data.get("fields", {})
                    return {
                        "key": data.get("key"),
                        "project": fields.get("project", {}).get("key"),
                        "summary": fields.get("summary"),
                        "issue_type": fields.get("issuetype", {}).get("name"),
                        "priority": fields.get("priority", {}).get("name"),
                        "status": fields.get("status", {}).get("name"),
                        "assignee": fields.get("assignee", {}).get("displayName", "Unassigned"),
                        "description": str(fields.get("description", "")),
                        "labels": fields.get("labels", []),
                    }
                return {"error": resp.status_code, "message": resp.text}
        except Exception as err:
            return {"error": "Live Jira API Connection Failed", "detail": str(err)}

    def _live_search(self, jql: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/rest/api/3/search"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    url,
                    auth=(self.email, self.api_token),
                    json={"jql": jql, "maxResults": 20},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    issues = []
                    for item in data.get("issues", []):
                        fields = item.get("fields", {})
                        issues.append({
                            "key": item.get("key"),
                            "project": fields.get("project", {}).get("key"),
                            "summary": fields.get("summary"),
                            "issue_type": fields.get("issuetype", {}).get("name"),
                            "priority": fields.get("priority", {}).get("name"),
                            "status": fields.get("status", {}).get("name"),
                            "assignee": fields.get("assignee", {}).get("displayName", "Unassigned"),
                            "labels": fields.get("labels", []),
                        })
                    return issues
                return []
        except Exception:
            return []


# Global client singleton
_jira_client: Optional[JiraClient] = None


def get_jira_client() -> JiraClient:
    """Singleton accessor for JiraClient."""
    global _jira_client
    if _jira_client is None:
        _jira_client = JiraClient()
    return _jira_client


# ==============================================================================
# Model Context Protocol (MCP) Tool Registrations
# ==============================================================================

@mcp_tool(
    name="jira_get_sprint_issues",
    description="Fetch current sprint issues from Jira with optional filtering by status (To Do, In Progress, Blocked, Done) or assignee.",
)
def jira_get_sprint_issues(
    project_key: str = "ALPHA",
    status: Optional[str] = None,
    assignee: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve active sprint issues for a project.

    Args:
        project_key: Project identifier (defaults to ALPHA).
        status: Filter by status (e.g. 'Blocked', 'In Progress', 'Done', 'To Do').
        assignee: Filter by assigned engineer's name.
    """
    client = get_jira_client()
    return client.get_sprint_issues(project_key=project_key, status=status, assignee=assignee)


@mcp_tool(
    name="jira_get_blockers",
    description="Find critical blocker issues and SEV-1/SEV-2 incidents currently impeding sprint delivery in Jira.",
)
def jira_get_blockers(project_key: str = "ALPHA") -> List[Dict[str, Any]]:
    """
    Identify active blockers and high-priority outages.

    Args:
        project_key: Project identifier (defaults to ALPHA).
    """
    client = get_jira_client()
    return client.get_blockers(project_key=project_key)


@mcp_tool(
    name="jira_get_issue_details",
    description="Retrieve complete metadata, description, priority, and status for a specific Jira issue (e.g. ALPHA-101).",
)
def jira_get_issue_details(issue_key: str) -> Dict[str, Any]:
    """
    Fetch single issue details.

    Args:
        issue_key: The issue key (e.g., 'ALPHA-101').
    """
    client = get_jira_client()
    return client.get_issue_details(issue_key=issue_key)


@mcp_tool(
    name="jira_search_issues",
    description="Search Jira issues by keyword, error message, or component across summaries, descriptions, and labels.",
)
def jira_search_issues(query: str, project_key: str = "ALPHA") -> List[Dict[str, Any]]:
    """
    Keyword search across project issues.

    Args:
        query: Keyword or phrase to search (e.g. 'payment', 'database', 'SEV-1').
        project_key: Project identifier (defaults to ALPHA).
    """
    client = get_jira_client()
    return client.search_issues(query=query, project_key=project_key)

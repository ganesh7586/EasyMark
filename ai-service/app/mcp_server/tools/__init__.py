"""
Model Context Protocol (MCP) Enterprise Tools Package.
"""

from app.mcp_server.tools.jira_tool import (
    JiraClient,
    get_jira_client,
    jira_get_blockers,
    jira_get_issue_details,
    jira_get_sprint_issues,
    jira_search_issues,
)
from app.mcp_server.tools.notion_tool import (
    NotionClient,
    get_notion_client,
    notion_get_action_items,
    notion_get_meeting_notes,
    notion_get_page,
    notion_search_pages,
)
from app.mcp_server.tools.gmail_tool import (
    GmailClient,
    get_gmail_client,
    gmail_check_pending_approvals,
    gmail_get_customer_escalations,
    gmail_get_thread,
    gmail_search_emails,
)

__all__ = [
    "GmailClient",
    "JiraClient",
    "NotionClient",
    "get_gmail_client",
    "get_jira_client",
    "get_notion_client",
    "gmail_check_pending_approvals",
    "gmail_get_customer_escalations",
    "gmail_get_thread",
    "gmail_search_emails",
    "jira_get_blockers",
    "jira_get_issue_details",
    "jira_get_sprint_issues",
    "jira_search_issues",
    "notion_get_action_items",
    "notion_get_meeting_notes",
    "notion_get_page",
    "notion_search_pages",
]

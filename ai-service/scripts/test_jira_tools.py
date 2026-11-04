"""
Script: test_jira_tools.py
Purpose: Interactive CLI demonstration of Jira MCP Tools (Live App #1).
Day 7 demonstration script.
"""

import json
from pathlib import Path
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.mcp_server.server import get_mcp_server
from app.mcp_server.tools.jira_tool import (
    get_jira_client,
    jira_get_blockers,
    jira_get_issue_details,
    jira_get_sprint_issues,
    jira_search_issues,
)


def print_section(title: str):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def main():
    print("=" * 70)
    print("[DAY 7] LIVE APP #1 — JIRA MODEL CONTEXT PROTOCOL (MCP) TOOLS DEMO")
    print("=" * 70)

    client = get_jira_client()
    mode = "Live Atlassian Cloud" if client.is_live else "Project Alpha Enterprise Dataset (Test Mode)"
    print(f"Operational Mode: {mode}")
    print(f"Target Project: {client.default_project}")

    # 1. Fetch Sprint Issues
    print_section("1. Fetch Sprint Issues (jira_get_sprint_issues)")
    issues = jira_get_sprint_issues(project_key="ALPHA")
    print(f"Found {len(issues)} issues in active sprint:")
    for issue in issues:
        print(f"  * [{issue['key']}] ({issue['status']:^11}) [{issue['priority']:^7}] {issue['summary']} -> {issue['assignee']}")

    # 2. Filter Issues by Status (Blocked)
    print_section("2. Filter Sprint Issues by Status: 'Blocked'")
    blocked = jira_get_sprint_issues(project_key="ALPHA", status="Blocked")
    print(f"Found {len(blocked)} blocked issues:")
    for b in blocked:
        print(f"  * [{b['key']}] {b['summary']} (Assignee: {b['assignee']})")

    # 3. Detect Critical Blockers (jira_get_blockers)
    print_section("3. Identify Critical Blockers & SEV Outages (jira_get_blockers)")
    blockers = jira_get_blockers(project_key="ALPHA")
    print(f"Found {len(blockers)} high-priority blockers:")
    for blk in blockers:
        print(f"  * [{blk['key']}] [{blk['priority']}] {blk['summary']}")
        print(f"    Labels: {blk['labels']}")
        print(f"    Details: {blk['description'][:100]}...\n")

    # 4. Fetch Detailed Issue (jira_get_issue_details: ALPHA-101)
    print_section("4. Inspect Single Issue Details (jira_get_issue_details: ALPHA-101)")
    detail = jira_get_issue_details("ALPHA-101")
    print(json.dumps(detail, indent=2))

    # 5. Search Issues by Keyword (jira_search_issues: 'database')
    print_section("5. Keyword Search across Issues (jira_search_issues: 'database')")
    search_results = jira_search_issues("database")
    print(f"Matched {len(search_results)} issue(s) matching keyword 'database':")
    for s in search_results:
        print(f"  * [{s['key']}] {s['summary']}")

    # 6. JSON-RPC 2.0 MCP Protocol Invocation via MCPServer
    print_section("6. MCP Server Protocol Call (JSON-RPC 2.0 tools/call: jira_get_blockers)")
    server = get_mcp_server()
    req = {
        "jsonrpc": "2.0",
        "id": "jira-demo-1",
        "method": "tools/call",
        "params": {
            "name": "jira_get_blockers",
            "arguments": {"project_key": "ALPHA"},
        },
    }
    resp = server.handle_message_sync(req)
    print("[JSON-RPC Response]:")
    print(json.dumps(resp, indent=2))

    print("\n" + "=" * 70)
    print("[SUCCESS] Day 7 Jira MCP Tools verified successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()

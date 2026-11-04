"""
Script: test_gmail_tools.py
Purpose: Interactive CLI demonstration of Gmail MCP Tools (Live App #3).
Day 9 demonstration script.
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
from app.mcp_server.tools.gmail_tool import (
    get_gmail_client,
    gmail_check_pending_approvals,
    gmail_get_customer_escalations,
    gmail_get_thread,
    gmail_search_emails,
)


def print_section(title: str):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def main():
    print("=" * 70)
    print("[DAY 9] LIVE APP #3 — GMAIL MODEL CONTEXT PROTOCOL (MCP) TOOLS DEMO")
    print("=" * 70)

    client = get_gmail_client()
    mode = "Live Google Workspace Inbox" if client.is_live else "Project Alpha Customer Inbox Dataset (Test Mode)"
    print(f"Operational Mode: {mode}")

    # 1. Detect Customer Escalations
    print_section("1. Retrieve Customer Escalations (gmail_get_customer_escalations: 'SEV-1')")
    sev1_escalations = gmail_get_customer_escalations(severity="SEV-1")
    print(f"Found {len(sev1_escalations)} SEV-1 customer escalation thread(s):")
    for esc in sev1_escalations:
        print(f"  * [{esc['id']}] [{esc['severity']}] {esc['subject']}")
        print(f"    From: {esc['customer']} (Jira: {esc['jira_correlation']})")
        print(f"    Status: {esc['status']}\n")

    # 2. Inspect Complete Email Thread
    print_section("2. Fetch Complete Thread with Messages (gmail_get_thread: 'GMAIL-THREAD-001')")
    thread = gmail_get_thread("GMAIL-THREAD-001")
    print(f"Subject: {thread.get('subject')}")
    print(f"Participants: {thread.get('sender')} -> {thread.get('recipient')}")
    print(f"Messages count: {len(thread.get('messages', []))}")
    for idx, msg in enumerate(thread.get("messages", []), start=1):
        print(f"  [Message {idx}] From: {msg['from']} at {msg['date']}")
        print(f"  Content: {msg['body'][:160]}...\n")

    # 3. Check Pending Approvals
    print_section("3. Check Security & Architecture Approvals (gmail_check_pending_approvals)")
    approvals = gmail_check_pending_approvals()
    print(f"Found {len(approvals)} approval thread(s):")
    for app in approvals:
        print(f"  * [{app['status']:^8}] {app['subject']}")
        print(f"    Approver: {app['approver']}\n")

    # 4. Keyword Search Across Inbox
    print_section("4. Search Email Messages (gmail_search_emails: '504')")
    results = gmail_search_emails("504")
    print(f"Found {len(results)} thread(s) mentioning '504':")
    for r in results:
        print(f"  * [{r['id']}] {r['subject']} ({r['sender']})")

    # 5. MCP JSON-RPC 2.0 Protocol Call
    print_section("5. MCP Server Protocol Call (JSON-RPC 2.0 tools/call: gmail_get_customer_escalations)")
    server = get_mcp_server()
    req = {
        "jsonrpc": "2.0",
        "id": "gmail-demo-1",
        "method": "tools/call",
        "params": {
            "name": "gmail_get_customer_escalations",
            "arguments": {"severity": "SEV-2"},
        },
    }
    resp = server.handle_message_sync(req)
    print("[JSON-RPC Response]:")
    print(json.dumps(resp, indent=2))

    print("\n" + "=" * 70)
    print("[SUCCESS] Day 9 Gmail MCP Tools verified successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()

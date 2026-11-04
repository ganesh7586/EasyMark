"""
Script: test_notion_tools.py
Purpose: Interactive CLI demonstration of Notion MCP Tools (Live App #2).
Day 8 demonstration script.
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
from app.mcp_server.tools.notion_tool import (
    get_notion_client,
    notion_get_action_items,
    notion_get_meeting_notes,
    notion_get_page,
    notion_search_pages,
)


def print_section(title: str):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def main():
    print("=" * 70)
    print("[DAY 8] LIVE APP #2 — NOTION MODEL CONTEXT PROTOCOL (MCP) TOOLS DEMO")
    print("=" * 70)

    client = get_notion_client()
    mode = "Live Notion Workspace" if client.is_live else "Project Alpha Documentation Dataset (Test Mode)"
    print(f"Operational Mode: {mode}")

    # 1. Search Notion Pages
    print_section("1. Search Documentation Pages (notion_search_pages: 'connection pool')")
    search_res = notion_search_pages("connection pool")
    print(f"Found {len(search_res)} matching documentation page(s):")
    for page in search_res:
        print(f"  * [{page['id']}] {page['title']} (Category: {page['category']})")
        print(f"    Summary: {page['summary']}\n")

    # 2. Get Full Page Document (notion_get_page: 'NOTION-SPEC-01')
    print_section("2. Fetch Full Architecture Spec (notion_get_page: 'NOTION-SPEC-01')")
    spec = notion_get_page("NOTION-SPEC-01")
    print(f"Title: {spec.get('title')}")
    print(f"Author: {spec.get('author')} ({spec.get('author_role')})")
    print(f"Content Preview:\n{spec.get('content')[:280]}...\n")

    # 3. Retrieve Meeting Notes
    print_section("3. Retrieve Engineering Meeting Notes (notion_get_meeting_notes)")
    notes = notion_get_meeting_notes()
    print(f"Retrieved {len(notes)} meeting note record(s):")
    for note in notes:
        print(f"  * [{note['date']}] {note['title']}")
        print(f"    Attendees: {', '.join(note['attendees'])}")
        print(f"    Summary: {note['summary']}\n")

    # 4. Extract Action Items (Filtered by Sarah Chen)
    print_section("4. Filter Action Items (notion_get_action_items: 'Sarah Chen')")
    actions = notion_get_action_items(assignee="Sarah Chen")
    print(f"Found {len(actions)} action item(s) assigned to Sarah Chen:")
    for a in actions:
        print(f"  * [{a['status']:^9}] {a['task']} (Source: {a['source_title']})")

    # 5. MCP JSON-RPC 2.0 Protocol Call
    print_section("5. MCP Server Protocol Call (JSON-RPC 2.0 tools/call: notion_get_action_items)")
    server = get_mcp_server()
    req = {
        "jsonrpc": "2.0",
        "id": "notion-demo-1",
        "method": "tools/call",
        "params": {
            "name": "notion_get_action_items",
            "arguments": {"assignee": "Priyansh Sharma"},
        },
    }
    resp = server.handle_message_sync(req)
    print("[JSON-RPC Response]:")
    print(json.dumps(resp, indent=2))

    print("\n" + "=" * 70)
    print("[SUCCESS] Day 8 Notion MCP Tools verified successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()

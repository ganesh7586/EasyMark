"""
Script: test_mcp_aggregator.py
Purpose: Interactive CLI demonstration of Unified MCP Client & Tool Aggregator (Day 10).
Sprint 2 Finale demonstration.
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

from app.mcp_server.aggregator import get_mcp_aggregator


def print_section(title: str):
    print("\n" + "=" * 75)
    print(f" {title}")
    print("=" * 75)


def main():
    print("=" * 75)
    print("[DAY 10] UNIFIED MCP CLIENT & TOOL AGGREGATOR DEMO (SPRINT 2 FINALE)")
    print("=" * 75)

    aggregator = get_mcp_aggregator()

    # 1. Total Registered Tools & Category Breakdown
    print_section("1. Unified Tool Inventory & Domain Categorization")
    tools = aggregator.list_all_tools()
    print(f"Total Aggregated Tools: {len(tools)}")
    categories = ["jira", "notion", "gmail", "diagnostic"]
    for cat in categories:
        cat_tools = aggregator.get_tools_by_category(cat)
        print(f"\n  [{cat.upper()}] ({len(cat_tools)} tools):")
        for t in cat_tools:
            req_params = ", ".join(t.inputSchema.required) if t.inputSchema.required else "none"
            print(f"    * {t.name:<32} (Required: {req_params})")

    # 2. Schema Reflection for Groq / OpenAI LLM Function Calling
    print_section("2. OpenAI / Groq LLM Function Calling Schema Generation")
    function_specs = aggregator.to_openai_function_specs()
    print(f"Successfully generated {len(function_specs)} function calling specifications.")
    sample = function_specs[3]  # Pick a tool, e.g. jira_get_sprint_issues or first domain tool
    print("\nSample LLM Tool Specification Payload (OpenAI format):")
    print(json.dumps(sample, indent=2))

    # 3. Dynamic Tool Discovery / Relevance Matching
    print_section("3. Heuristic Tool Discovery for Natural Language Queries")
    sample_queries = [
        "What tickets are blocking sprint progress in Jira?",
        "Where can I find the meeting notes and architecture specs in Notion?",
        "Did any customer escalate 504 gateway timeout issues via Gmail?",
        "System ping and health status check",
    ]
    for q in sample_queries:
        matched = aggregator.find_relevant_tools(q)
        tool_names = [t.name for t in matched]
        print(f"\n  Query: \"{q}\"")
        print(f"  Matched Tools ({len(matched)}): {', '.join(tool_names)}")

    # 4. Multi-Domain Cross-Tool Storyline Execution
    print_section("4. Multi-Domain Storyline Execution (Jira -> Notion -> Gmail)")
    print("Scenario: Investigating incident ALPHA-101 across static & dynamic data.\n")

    # Step A: Jira Blocker
    print("[Step A: Querying Jira for active blockers]")
    jira_res = aggregator.execute_tool_sync("jira_get_blockers")
    print(f"  Tool: {jira_res['tool_name']} | Latency: {jira_res['latency_ms']} ms | Error: {jira_res['is_error']}")
    jira_data = json.loads(jira_res["content"][0]["text"])
    blocker = jira_data[0]
    print(f"  Identified Blocker: {blocker['key']} - {blocker['summary']} (Assignee: {blocker['assignee']})")

    # Step B: Notion Architecture Spec
    print("\n[Step B: Querying Notion for database connection pool specs]")
    notion_res = aggregator.execute_tool_sync("notion_get_page", {"page_id_or_title": "NOTION-SPEC-01"})
    print(f"  Tool: {notion_res['tool_name']} | Latency: {notion_res['latency_ms']} ms | Error: {notion_res['is_error']}")
    notion_data = json.loads(notion_res["content"][0]["text"])
    print(f"  Retrieved Spec: {notion_data['title']} (Author: {notion_data['author']})")
    print(f"  Excerpt: {notion_data['content'][:140]}...")

    # Step C: Gmail Customer Escalation
    print("\n[Step C: Querying Gmail for customer escalations related to ALPHA-101]")
    gmail_res = aggregator.execute_tool_sync("gmail_get_customer_escalations", {"severity": "SEV-1"})
    print(f"  Tool: {gmail_res['tool_name']} | Latency: {gmail_res['latency_ms']} ms | Error: {gmail_res['is_error']}")
    gmail_data = json.loads(gmail_res["content"][0]["text"])
    escalation = gmail_data[0]
    print(f"  Customer Escalation: {escalation['subject']} from {escalation['customer']}")
    print(f"  Correlated Jira Ticket: {escalation['jira_correlation']}")

    print("\n" + "=" * 75)
    print(">>> SPRINT 2 (DAYS 6-10) DEMONSTRATION COMPLETE: ALL 15 TOOLS UNIFIED <<<")
    print("=" * 75)


if __name__ == "__main__":
    main()

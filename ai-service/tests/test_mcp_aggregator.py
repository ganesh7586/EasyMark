"""
Unit and integration tests for Unified MCP Client & Tool Aggregator (Day 10).
Sprint 2 verification suite for Company Intelligence AI.
"""

import json
import pytest

from app.mcp_server.aggregator import (
    AggregatedToolSummary,
    UnifiedMCPAggregator,
    get_mcp_aggregator,
)
from app.mcp_server.server import get_mcp_server
from app.mcp_server.transport import create_mcp_router


def run_coroutine(coro):
    """Directly drives coroutines synchronously without spinning up socket-bound loops."""
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value


@pytest.fixture
def aggregator():
    """Provides the singleton UnifiedMCPAggregator."""
    return get_mcp_aggregator()


class TestMCPAggregatorToolInventory:
    """Tests for tool registry aggregation and category breakdown."""

    def test_total_tool_count(self, aggregator):
        tools = aggregator.list_all_tools()
        assert len(tools) == 15, f"Expected 15 total tools, found {len(tools)}"

    def test_category_breakdown(self, aggregator):
        jira_tools = aggregator.get_tools_by_category("jira")
        notion_tools = aggregator.get_tools_by_category("notion")
        gmail_tools = aggregator.get_tools_by_category("gmail")
        diagnostic_tools = aggregator.get_tools_by_category("diagnostic")

        assert len(jira_tools) == 4
        assert len(notion_tools) == 4
        assert len(gmail_tools) == 4
        assert len(diagnostic_tools) == 3

    def test_tool_names_in_categories(self, aggregator):
        jira_names = {t.name for t in aggregator.get_tools_by_category("jira")}
        assert jira_names == {
            "jira_get_sprint_issues",
            "jira_get_blockers",
            "jira_get_issue_details",
            "jira_search_issues",
        }

        notion_names = {t.name for t in aggregator.get_tools_by_category("notion")}
        assert notion_names == {
            "notion_get_page",
            "notion_search_pages",
            "notion_get_meeting_notes",
            "notion_get_action_items",
        }

        gmail_names = {t.name for t in aggregator.get_tools_by_category("gmail")}
        assert gmail_names == {
            "gmail_get_thread",
            "gmail_search_emails",
            "gmail_get_customer_escalations",
            "gmail_check_pending_approvals",
        }

        diag_names = {t.name for t in aggregator.get_tools_by_category("diagnostic")}
        assert diag_names == {"system_health", "echo_message", "ping"}

    def test_get_tool_summaries(self, aggregator):
        summaries = aggregator.get_tool_summaries()
        assert len(summaries) == 15
        assert all(isinstance(s, AggregatedToolSummary) for s in summaries)

        jira_summary = next(s for s in summaries if s.name == "jira_get_blockers")
        assert jira_summary.category == "jira"
        assert "blocker" in jira_summary.description.lower()
        assert isinstance(jira_summary.required_parameters, list)


class TestMCPAggregatorSchemaReflection:
    """Tests for OpenAI / Groq LLM function calling schema conversion."""

    def test_openai_function_specs_structure(self, aggregator):
        specs = aggregator.to_openai_function_specs()
        assert len(specs) == 15

        for spec in specs:
            assert spec["type"] == "function"
            fn = spec["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn
            params = fn["parameters"]
            assert params["type"] == "object"
            assert "properties" in params
            assert "required" in params

    def test_specific_tool_schema(self, aggregator):
        specs = aggregator.to_openai_function_specs()
        gmail_thread_spec = next(s for s in specs if s["function"]["name"] == "gmail_get_thread")
        fn = gmail_thread_spec["function"]
        assert "thread_id" in fn["parameters"]["properties"]
        assert "thread_id" in fn["parameters"]["required"]


class TestMCPAggregatorDiscovery:
    """Tests for heuristic tool discovery and query routing."""

    def test_find_relevant_tools_jira(self, aggregator):
        matched = aggregator.find_relevant_tools("Show me sprint blockers in Jira")
        names = [t.name for t in matched]
        assert "jira_get_blockers" in names
        assert "jira_get_sprint_issues" in names

    def test_find_relevant_tools_notion(self, aggregator):
        matched = aggregator.find_relevant_tools("Find Notion meeting notes and architecture spec")
        names = [t.name for t in matched]
        assert "notion_get_meeting_notes" in names
        assert "notion_get_page" in names

    def test_find_relevant_tools_gmail(self, aggregator):
        matched = aggregator.find_relevant_tools("Are there customer email escalations in the inbox?")
        names = [t.name for t in matched]
        assert "gmail_get_customer_escalations" in names
        assert "gmail_search_emails" in names

    def test_find_relevant_tools_fallback(self, aggregator):
        # Query with no specific domain keywords should return all tools as fallback
        matched = aggregator.find_relevant_tools("Arbitrary query with no matching keywords")
        assert len(matched) == 15


class TestMCPAggregatorExecution:
    """Tests for tool execution, error handling, and latency profiling."""

    def test_execute_tool_async(self, aggregator):
        coro = aggregator.execute_tool("jira_get_blockers")
        res = run_coroutine(coro)

        assert res["tool_name"] == "jira_get_blockers"
        assert res["category"] == "jira"
        assert res["is_error"] is False
        assert res["latency_ms"] >= 0
        assert len(res["content"]) >= 1

        data = json.loads(res["content"][0]["text"])
        assert any(b["key"] == "ALPHA-101" for b in data)

    def test_execute_tool_sync(self, aggregator):
        res = aggregator.execute_tool_sync(
            "notion_get_page",
            {"page_id_or_title": "NOTION-SPEC-01"},
        )
        assert res["tool_name"] == "notion_get_page"
        assert res["category"] == "notion"
        assert res["is_error"] is False
        data = json.loads(res["content"][0]["text"])
        assert data["id"] == "NOTION-SPEC-01"

    def test_execute_nonexistent_tool(self, aggregator):
        coro = aggregator.execute_tool("nonexistent_tool_123")
        res = run_coroutine(coro)
        assert res["is_error"] is True
        assert "unknown tool" in res["content"][0]["text"].lower()


class TestMCPTransportEndpoints:
    """Tests for FastAPI HTTP schema and category endpoints."""

    def test_schema_endpoint(self):
        server = get_mcp_server()
        router = create_mcp_router(server)
        schema_endpoint = next(
            r.endpoint for r in router.routes
            if getattr(r, "path", None) == "/api/v1/mcp/schema"
        )
        result = run_coroutine(schema_endpoint(_auth="test-key"))
        assert result["count"] == 15
        assert len(result["tools"]) == 15

    def test_categories_endpoint(self):
        server = get_mcp_server()
        router = create_mcp_router(server)
        cat_endpoint = next(
            r.endpoint for r in router.routes
            if getattr(r, "path", None) == "/api/v1/mcp/categories"
        )
        breakdown = run_coroutine(cat_endpoint(_auth="test-key"))
        assert "jira" in breakdown
        assert "notion" in breakdown
        assert "gmail" in breakdown
        assert "diagnostic" in breakdown
        assert len(breakdown["jira"]) == 4
        assert len(breakdown["notion"]) == 4
        assert len(breakdown["gmail"]) == 4
        assert len(breakdown["diagnostic"]) == 3

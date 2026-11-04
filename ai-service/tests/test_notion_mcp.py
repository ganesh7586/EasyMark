"""
Unit and integration tests for Notion Model Context Protocol (MCP) Tools.
Day 8 verification suite for Company Intelligence AI.
"""

import json
from fastapi import HTTPException
import pytest

from app.mcp_server.models import CallToolResult
from app.mcp_server.registry import default_registry
from app.mcp_server.server import get_mcp_server
from app.mcp_server.tools.notion_tool import (
    NotionClient,
    get_notion_client,
    notion_get_action_items,
    notion_get_meeting_notes,
    notion_get_page,
    notion_search_pages,
)
from app.mcp_server.transport import DirectToolCallRequest, create_mcp_router


def run_coroutine(coro):
    """Directly drives coroutines synchronously without spinning up socket-bound loops."""
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value


@pytest.fixture
def notion_client():
    """Provides a NotionClient in dataset test mode."""
    return NotionClient(api_key=None, database_id=None)


class TestNotionClientUnit:
    """Unit tests for NotionClient document lookup and action item parsing."""

    def test_get_page_by_valid_id(self, notion_client):
        page = notion_client.get_page("NOTION-SPEC-01")
        assert page["id"] == "NOTION-SPEC-01"
        assert "Architecture" in page["title"]
        assert page["author"] == "Sarah Chen"
        assert "minPoolSize" in page["content"]

    def test_get_page_by_title_substring(self, notion_client):
        page = notion_client.get_page("Meeting Notes")
        assert page["id"] == "NOTION-NOTE-02"
        assert page["category"] == "Meeting Notes"

    def test_get_page_invalid_returns_error(self, notion_client):
        result = notion_client.get_page("NON_EXISTENT_PAGE_123")
        assert "error" in result
        assert result["error"] == "Not Found"

    def test_search_pages_keyword(self, notion_client):
        results = notion_client.search_pages("citations")
        assert len(results) >= 2
        titles = [p["title"] for p in results]
        assert any("PRD" in t for t in titles)

    def test_search_pages_no_match(self, notion_client):
        results = notion_client.search_pages("completely_random_term_not_found")
        assert results == []

    def test_get_meeting_notes_all(self, notion_client):
        notes = notion_client.get_meeting_notes()
        assert len(notes) >= 1
        assert notes[0]["category"] == "Meeting Notes"
        assert "Sarah Chen" in notes[0]["attendees"]

    def test_get_meeting_notes_filtered_by_tag(self, notion_client):
        notes = notion_client.get_meeting_notes(date_or_tag="weekly")
        assert len(notes) >= 1
        assert "weekly" in notes[0]["tags"]

    def test_get_action_items_all(self, notion_client):
        items = notion_client.get_action_items()
        assert len(items) >= 4
        assignees = [i["assignee"] for i in items]
        assert "Sarah Chen" in assignees
        assert "Alex Rivera" in assignees

    def test_get_action_items_filtered_by_assignee(self, notion_client):
        items = notion_client.get_action_items(assignee="Alex Rivera")
        assert len(items) == 1
        assert items[0]["assignee"] == "Alex Rivera"
        assert items[0]["status"] == "Completed"


class TestNotionMCPToolRegistration:
    """Verifies that Notion tools are properly registered in the global ToolRegistry."""

    def test_all_four_notion_tools_registered(self):
        registered_names = [t.name for t in default_registry.list_tools()]
        assert "notion_get_page" in registered_names
        assert "notion_search_pages" in registered_names
        assert "notion_get_meeting_notes" in registered_names
        assert "notion_get_action_items" in registered_names

    def test_notion_tool_schema_reflection(self):
        tool = default_registry.get_tool("notion_get_page")
        assert tool is not None
        schema = tool.input_schema
        assert schema.type == "object"
        assert "page_id_or_title" in schema.properties
        assert schema.properties["page_id_or_title"]["type"] == "string"
        assert "page_id_or_title" in schema.required


class TestNotionMCPJSONRPCExecution:
    """Verifies executing Notion tools via standard MCP JSON-RPC 2.0 messages."""

    def test_jsonrpc_call_notion_get_page(self):
        server = get_mcp_server()
        req = {
            "jsonrpc": "2.0",
            "id": "notion-test-1",
            "method": "tools/call",
            "params": {
                "name": "notion_get_page",
                "arguments": {"page_id_or_title": "NOTION-PRD-03"},
            },
        }
        resp = server.handle_message_sync(req)
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == "notion-test-1"
        assert resp["result"]["isError"] is False
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["id"] == "NOTION-PRD-03"
        assert content["author"] == "Emily Watson"

    def test_jsonrpc_call_notion_get_action_items(self):
        server = get_mcp_server()
        req = {
            "jsonrpc": "2.0",
            "id": "notion-test-2",
            "method": "tools/call",
            "params": {
                "name": "notion_get_action_items",
                "arguments": {"assignee": "Maya Lin"},
            },
        }
        resp = server.handle_message_sync(req)
        assert resp["result"]["isError"] is False
        items = json.loads(resp["result"]["content"][0]["text"])
        assert len(items) == 1
        assert items[0]["assignee"] == "Maya Lin"


class TestFastAPIMCPNotionRoute:
    """Verifies invoking Notion tools via the FastAPI /api/v1/mcp endpoint."""

    def test_direct_tool_call_endpoint_notion_action_items(self):
        server = get_mcp_server()
        router = create_mcp_router(server=server)
        call_endpoint = next(
            r.endpoint for r in router.routes if r.path == "/api/v1/mcp/tools/call" and "POST" in r.methods
        )

        payload = DirectToolCallRequest(
            name="notion_get_action_items",
            arguments={"assignee": "Sarah Chen"},
        )
        result: CallToolResult = run_coroutine(call_endpoint(payload=payload, _auth="authorized_key"))
        assert result.isError is False
        parsed = json.loads(result.content[0].text)
        assert len(parsed) >= 2

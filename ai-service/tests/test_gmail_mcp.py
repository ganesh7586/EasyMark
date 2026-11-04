"""
Unit and integration tests for Gmail Model Context Protocol (MCP) Tools.
Day 9 verification suite for Company Intelligence AI.
"""

import json
from fastapi import HTTPException
import pytest

from app.mcp_server.models import CallToolResult
from app.mcp_server.registry import default_registry
from app.mcp_server.server import get_mcp_server
from app.mcp_server.tools.gmail_tool import (
    GmailClient,
    get_gmail_client,
    gmail_check_pending_approvals,
    gmail_get_customer_escalations,
    gmail_get_thread,
    gmail_search_emails,
)
from app.mcp_server.transport import DirectToolCallRequest, create_mcp_router


def run_coroutine(coro):
    """Directly drives coroutines synchronously without spinning up socket-bound loops."""
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value


@pytest.fixture
def gmail_client():
    """Provides a GmailClient in dataset test mode."""
    return GmailClient(client_id=None, client_secret=None, refresh_token=None)


class TestGmailClientUnit:
    """Unit tests for GmailClient email parsing and escalation detection."""

    def test_get_thread_valid(self, gmail_client):
        thread = gmail_client.get_thread("GMAIL-THREAD-001")
        assert thread["id"] == "GMAIL-THREAD-001"
        assert thread["severity"] == "SEV-1"
        assert thread["jira_correlation"] == "ALPHA-101"
        assert len(thread["messages"]) == 2

    def test_get_thread_invalid_returns_error(self, gmail_client):
        result = gmail_client.get_thread("NON_EXISTENT_THREAD_999")
        assert "error" in result
        assert result["error"] == "Not Found"

    def test_search_emails_by_keyword(self, gmail_client):
        matches = gmail_client.search_emails("Acme Corp")
        assert len(matches) == 1
        assert matches[0]["id"] == "GMAIL-THREAD-001"
        assert "504" in matches[0]["subject"]

    def test_search_emails_no_match(self, gmail_client):
        results = gmail_client.search_emails("nonexistent_random_phrase_xyz")
        assert results == []

    def test_get_customer_escalations_all(self, gmail_client):
        escalations = gmail_client.get_customer_escalations()
        assert len(escalations) == 2
        severities = [e["severity"] for e in escalations]
        assert "SEV-1" in severities
        assert "SEV-2" in severities

    def test_get_customer_escalations_filtered_by_severity(self, gmail_client):
        sev1 = gmail_client.get_customer_escalations(severity="SEV-1")
        assert len(sev1) == 1
        assert sev1[0]["id"] == "GMAIL-THREAD-001"
        assert sev1[0]["jira_correlation"] == "ALPHA-101"

    def test_check_pending_approvals(self, gmail_client):
        approvals = gmail_client.check_pending_approvals()
        assert len(approvals) >= 1
        assert "Security Audit Sign-Off" in approvals[0]["subject"]
        assert approvals[0]["status"] == "Approved"


class TestGmailMCPToolsRegistration:
    """Verifies that Gmail tools are properly registered in the global ToolRegistry."""

    def test_all_four_gmail_tools_registered(self):
        registered_names = [t.name for t in default_registry.list_tools()]
        assert "gmail_get_thread" in registered_names
        assert "gmail_search_emails" in registered_names
        assert "gmail_get_customer_escalations" in registered_names
        assert "gmail_check_pending_approvals" in registered_names

    def test_gmail_tool_schema_reflection(self):
        tool = default_registry.get_tool("gmail_get_thread")
        assert tool is not None
        schema = tool.input_schema
        assert schema.type == "object"
        assert "thread_id" in schema.properties
        assert schema.properties["thread_id"]["type"] == "string"
        assert "thread_id" in schema.required


class TestGmailMCPJSONRPCExecution:
    """Verifies executing Gmail tools via standard MCP JSON-RPC 2.0 messages."""

    def test_jsonrpc_call_gmail_get_thread(self):
        server = get_mcp_server()
        req = {
            "jsonrpc": "2.0",
            "id": "gmail-test-1",
            "method": "tools/call",
            "params": {
                "name": "gmail_get_thread",
                "arguments": {"thread_id": "GMAIL-THREAD-001"},
            },
        }
        resp = server.handle_message_sync(req)
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == "gmail-test-1"
        assert resp["result"]["isError"] is False
        thread = json.loads(resp["result"]["content"][0]["text"])
        assert thread["id"] == "GMAIL-THREAD-001"
        assert thread["severity"] == "SEV-1"

    def test_jsonrpc_call_gmail_get_customer_escalations(self):
        server = get_mcp_server()
        req = {
            "jsonrpc": "2.0",
            "id": "gmail-test-2",
            "method": "tools/call",
            "params": {
                "name": "gmail_get_customer_escalations",
                "arguments": {"severity": "SEV-2"},
            },
        }
        resp = server.handle_message_sync(req)
        assert resp["result"]["isError"] is False
        escalations = json.loads(resp["result"]["content"][0]["text"])
        assert len(escalations) == 1
        assert escalations[0]["id"] == "GMAIL-THREAD-002"


class TestFastAPIMCPGmailRoute:
    """Verifies invoking Gmail tools via the FastAPI /api/v1/mcp endpoint."""

    def test_direct_tool_call_endpoint_gmail_approvals(self):
        server = get_mcp_server()
        router = create_mcp_router(server=server)
        call_endpoint = next(
            r.endpoint for r in router.routes if r.path == "/api/v1/mcp/tools/call" and "POST" in r.methods
        )

        payload = DirectToolCallRequest(
            name="gmail_check_pending_approvals",
            arguments={},
        )
        result: CallToolResult = run_coroutine(call_endpoint(payload=payload, _auth="authorized_key"))
        assert result.isError is False
        parsed = json.loads(result.content[0].text)
        assert len(parsed) >= 1

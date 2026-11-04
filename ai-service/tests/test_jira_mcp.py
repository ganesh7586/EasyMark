"""
Unit and integration tests for Jira Model Context Protocol (MCP) Tools.
Day 7 verification suite for Company Intelligence AI.
"""

import json
from fastapi import HTTPException
import pytest

from app.mcp_server.models import CallToolResult
from app.mcp_server.registry import default_registry
from app.mcp_server.server import get_mcp_server
from app.mcp_server.tools.jira_tool import (
    JiraClient,
    get_jira_client,
    jira_get_blockers,
    jira_get_issue_details,
    jira_get_sprint_issues,
    jira_search_issues,
)
from app.mcp_server.transport import DirectToolCallRequest, create_mcp_router


def run_coroutine(coro):
    """Directly drives coroutines synchronously without spinning up socket-bound loops."""
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value


@pytest.fixture
def jira_client():
    """Provides a JiraClient in dataset test mode."""
    return JiraClient(base_url=None, email=None, api_token=None, default_project="ALPHA")


class TestJiraClientUnit:
    """Unit tests for JiraClient query methods and filtering."""

    def test_get_all_sprint_issues(self, jira_client):
        issues = jira_client.get_sprint_issues(project_key="ALPHA")
        assert len(issues) == 6
        assert all(i["project"] == "ALPHA" for i in issues)

    def test_filter_sprint_issues_by_status(self, jira_client):
        blocked = jira_client.get_sprint_issues(project_key="ALPHA", status="Blocked")
        assert len(blocked) == 2
        keys = [b["key"] for b in blocked]
        assert "ALPHA-101" in keys
        assert "ALPHA-104" in keys

        done = jira_client.get_sprint_issues(project_key="ALPHA", status="Done")
        assert len(done) == 1
        assert done[0]["key"] == "ALPHA-103"

    def test_filter_sprint_issues_by_assignee(self, jira_client):
        sarah_issues = jira_client.get_sprint_issues(project_key="ALPHA", assignee="Sarah Chen")
        assert len(sarah_issues) == 2
        for issue in sarah_issues:
            assert "Sarah Chen" in issue["assignee"]

    def test_get_blockers_detects_sev_incidents(self, jira_client):
        blockers = jira_client.get_blockers(project_key="ALPHA")
        assert len(blockers) >= 2
        blocker_keys = [b["key"] for b in blockers]
        assert "ALPHA-101" in blocker_keys  # SEV-1
        assert "ALPHA-104" in blocker_keys  # SEV-2

    def test_get_issue_details_valid(self, jira_client):
        issue = jira_client.get_issue_details("ALPHA-101")
        assert issue["key"] == "ALPHA-101"
        assert issue["priority"] == "Highest"
        assert issue["status"] == "Blocked"
        assert "Payments API" in issue["summary"]
        assert "SEV-1" in issue["description"]

    def test_get_issue_details_invalid_returns_error(self, jira_client):
        result = jira_client.get_issue_details("ALPHA-9999")
        assert "error" in result
        assert result["error"] == "Not Found"

    def test_search_issues_by_keyword(self, jira_client):
        db_issues = jira_client.search_issues("database", project_key="ALPHA")
        assert len(db_issues) == 2
        keys = [i["key"] for i in db_issues]
        assert "ALPHA-101" in keys
        assert "ALPHA-103" in keys

    def test_search_issues_no_matches(self, jira_client):
        results = jira_client.search_issues("nonexistent_keyword_xyz", project_key="ALPHA")
        assert results == []


class TestJiraMCPToolRegistration:
    """Verifies that Jira tools are properly registered into the global ToolRegistry."""

    def test_all_four_jira_tools_registered(self):
        registered_names = [t.name for t in default_registry.list_tools()]
        assert "jira_get_sprint_issues" in registered_names
        assert "jira_get_blockers" in registered_names
        assert "jira_get_issue_details" in registered_names
        assert "jira_search_issues" in registered_names

    def test_jira_tool_schema_reflection(self):
        tool = default_registry.get_tool("jira_get_issue_details")
        assert tool is not None
        schema = tool.input_schema
        assert schema.type == "object"
        assert "issue_key" in schema.properties
        assert schema.properties["issue_key"]["type"] == "string"
        assert "issue_key" in schema.required


class TestJiraMCPJSONRPCExecution:
    """Verifies executing Jira tools via standard MCP JSON-RPC 2.0 messages."""

    def test_jsonrpc_call_jira_get_blockers(self):
        server = get_mcp_server()
        req = {
            "jsonrpc": "2.0",
            "id": "jira-test-1",
            "method": "tools/call",
            "params": {
                "name": "jira_get_blockers",
                "arguments": {"project_key": "ALPHA"},
            },
        }
        resp = server.handle_message_sync(req)
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == "jira-test-1"
        assert resp["result"]["isError"] is False

        # Parse content text
        content_text = resp["result"]["content"][0]["text"]
        parsed = json.loads(content_text)
        assert isinstance(parsed, list)
        assert len(parsed) >= 2
        assert any(i["key"] == "ALPHA-101" for i in parsed)

    def test_jsonrpc_call_jira_get_issue_details(self):
        server = get_mcp_server()
        req = {
            "jsonrpc": "2.0",
            "id": "jira-test-2",
            "method": "tools/call",
            "params": {
                "name": "jira_get_issue_details",
                "arguments": {"issue_key": "ALPHA-102"},
            },
        }
        resp = server.handle_message_sync(req)
        assert resp["result"]["isError"] is False
        content_text = resp["result"]["content"][0]["text"]
        issue = json.loads(content_text)
        assert issue["key"] == "ALPHA-102"
        assert issue["assignee"] == "Alex Rivera"

    def test_jsonrpc_call_missing_required_argument(self):
        server = get_mcp_server()
        req = {
            "jsonrpc": "2.0",
            "id": "jira-test-3",
            "method": "tools/call",
            "params": {
                "name": "jira_get_issue_details",
                "arguments": {},  # Missing required 'issue_key'
            },
        }
        resp = server.handle_message_sync(req)
        assert resp["result"]["isError"] is True
        assert "Missing required argument 'issue_key'" in resp["result"]["content"][0]["text"]


class TestFastAPIMCPJiraRoute:
    """Verifies invoking Jira tools via the FastAPI /api/v1/mcp endpoint."""

    def test_direct_tool_call_endpoint_jira_blockers(self):
        server = get_mcp_server()
        router = create_mcp_router(server=server)
        call_endpoint = next(
            r.endpoint for r in router.routes if r.path == "/api/v1/mcp/tools/call" and "POST" in r.methods
        )

        payload = DirectToolCallRequest(
            name="jira_get_blockers",
            arguments={"project_key": "ALPHA"},
        )
        result: CallToolResult = run_coroutine(call_endpoint(payload=payload, _auth="authorized_key"))
        assert result.isError is False
        parsed = json.loads(result.content[0].text)
        assert len(parsed) >= 2

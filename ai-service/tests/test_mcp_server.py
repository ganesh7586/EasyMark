"""
Unit and integration tests for Model Context Protocol (MCP) Server.
Day 6 verification suite for Company Intelligence AI.
"""

from fastapi import HTTPException
import pytest

from app.core.config import settings
from app.mcp_server.models import (
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    CallToolResult,
)
from app.mcp_server.registry import ToolRegistry, mcp_tool
from app.mcp_server.server import MCPServer
from app.mcp_server.transport import (
    DirectToolCallRequest,
    create_mcp_router,
)


def run_coroutine(coro):
    """Directly drives coroutines synchronously without spinning up socket-bound loops."""
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value


@pytest.fixture
def custom_registry():
    """Provides an isolated ToolRegistry for unit tests."""
    reg = ToolRegistry()

    @reg.register(name="add_numbers", description="Add two integers.")
    def add(a: int, b: int) -> int:
        return a + b

    @reg.register(name="async_multiply", description="Multiply two numbers asynchronously.")
    async def multiply(x: int, y: int = 2) -> int:
        return x * y

    @reg.register(name="failing_tool", description="Tool that raises an error.")
    def fail():
        raise ValueError("Simulated tool crash")

    return reg


@pytest.fixture
def test_server(custom_registry):
    """Provides an MCPServer backed by the isolated test registry."""
    return MCPServer(
        name="test-mcp-server",
        version="0.1.0",
        registry=custom_registry,
    )


class TestMCPServerProtocol:
    """Tests for MCP JSON-RPC 2.0 protocol dispatch and methods."""

    def test_initialize_handshake(self, test_server):
        req = {
            "jsonrpc": "2.0",
            "id": "init-1",
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        }
        res = test_server.handle_message_sync(req)
        assert res["jsonrpc"] == "2.0"
        assert res["id"] == "init-1"
        assert "result" in res
        assert res["result"]["protocolVersion"] == "2024-11-05"
        assert res["result"]["serverInfo"]["name"] == "test-mcp-server"
        assert "tools" in res["result"]["capabilities"]
        assert test_server.initialized is True

    def test_ping(self, test_server):
        req = {"jsonrpc": "2.0", "id": 100, "method": "ping"}
        res = test_server.handle_message_sync(req)
        assert res["jsonrpc"] == "2.0"
        assert res["id"] == 100
        assert res["result"] == {}

    def test_notifications_return_none(self, test_server):
        req = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        res = test_server.handle_message_sync(req)
        assert res is None

    def test_tools_list_schema_reflection(self, test_server):
        req = {"jsonrpc": "2.0", "id": "list-1", "method": "tools/list"}
        res = test_server.handle_message_sync(req)
        assert res["id"] == "list-1"
        tools = res["result"]["tools"]
        assert len(tools) == 3

        tool_names = [t["name"] for t in tools]
        assert "add_numbers" in tool_names
        assert "async_multiply" in tool_names
        assert "failing_tool" in tool_names

        # Validate schema of add_numbers
        add_tool = next(t for t in tools if t["name"] == "add_numbers")
        assert add_tool["inputSchema"]["type"] == "object"
        assert "a" in add_tool["inputSchema"]["properties"]
        assert "b" in add_tool["inputSchema"]["properties"]
        assert "a" in add_tool["inputSchema"]["required"]
        assert "b" in add_tool["inputSchema"]["required"]

    def test_tools_call_sync_success(self, test_server):
        req = {
            "jsonrpc": "2.0",
            "id": 201,
            "method": "tools/call",
            "params": {"name": "add_numbers", "arguments": {"a": 15, "b": 27}},
        }
        res = test_server.handle_message_sync(req)
        assert res["id"] == 201
        assert res["result"]["isError"] is False
        assert res["result"]["content"][0]["text"] == "42"

    def test_tools_call_async_success(self, test_server):
        req = {
            "jsonrpc": "2.0",
            "id": 202,
            "method": "tools/call",
            "params": {"name": "async_multiply", "arguments": {"x": 7, "y": 6}},
        }
        res = test_server.handle_message_sync(req)
        assert res["id"] == 202
        assert res["result"]["isError"] is False
        assert res["result"]["content"][0]["text"] == "42"

    def test_tools_call_missing_required_param(self, test_server):
        req = {
            "jsonrpc": "2.0",
            "id": 203,
            "method": "tools/call",
            "params": {"name": "add_numbers", "arguments": {"a": 10}},  # Missing 'b'
        }
        res = test_server.handle_message_sync(req)
        assert res["result"]["isError"] is True
        assert "Missing required argument 'b'" in res["result"]["content"][0]["text"]

    def test_tools_call_unknown_tool(self, test_server):
        req = {
            "jsonrpc": "2.0",
            "id": 204,
            "method": "tools/call",
            "params": {"name": "imaginary_tool", "arguments": {}},
        }
        res = test_server.handle_message_sync(req)
        assert res["result"]["isError"] is True
        assert "Unknown tool 'imaginary_tool'" in res["result"]["content"][0]["text"]

    def test_tools_call_failing_tool_graceful_handling(self, test_server):
        req = {
            "jsonrpc": "2.0",
            "id": 205,
            "method": "tools/call",
            "params": {"name": "failing_tool", "arguments": {}},
        }
        res = test_server.handle_message_sync(req)
        assert res["result"]["isError"] is True
        assert "Simulated tool crash" in res["result"]["content"][0]["text"]

    def test_unknown_method_error_32601(self, test_server):
        req = {"jsonrpc": "2.0", "id": 404, "method": "unsupported/method"}
        res = test_server.handle_message_sync(req)
        assert res["error"]["code"] == METHOD_NOT_FOUND
        assert "Method not found" in res["error"]["message"]

    def test_malformed_json_parse_error_32700(self, test_server):
        res = test_server.handle_message_sync("{bad json: true")
        assert res["error"]["code"] == PARSE_ERROR

    def test_invalid_request_missing_method(self, test_server):
        res = test_server.handle_message_sync({"jsonrpc": "2.0", "id": 1})
        assert res["error"]["code"] == INVALID_REQUEST

    def test_tools_call_missing_name_error_32602(self, test_server):
        req = {"jsonrpc": "2.0", "id": 500, "method": "tools/call", "params": {}}
        res = test_server.handle_message_sync(req)
        assert res["error"]["code"] == INVALID_PARAMS


class TestBuiltinDiagnosticTools:
    """Tests for the out-of-the-box system diagnostic tools."""

    def test_system_health_tool_execution(self):
        from app.mcp_server.diagnostic_tools import system_health
        health = system_health(detailed=True)
        assert health["status"] == "healthy"
        assert health["service"] == settings.PROJECT_NAME
        assert health["registered_mcp_tools"] >= 3
        assert "system" in health
        assert "python_version" in health["system"]

    def test_echo_message_tool_execution(self):
        from app.mcp_server.diagnostic_tools import echo_message
        assert echo_message("hello", uppercase=False) == "hello"
        assert echo_message("hello", uppercase=True) == "HELLO"

    def test_ping_tool_execution(self):
        from app.mcp_server.diagnostic_tools import ping
        assert ping() == "pong"


class TestFastAPIMCPTransportRoutes:
    """Tests for the /api/v1/mcp router endpoints."""

    def test_router_list_tools_endpoint(self, test_server):
        router = create_mcp_router(server=test_server)
        list_endpoint = next(r.endpoint for r in router.routes if r.path == "/api/v1/mcp/tools" and "GET" in r.methods)
        
        response = run_coroutine(list_endpoint(_auth="authorized_key"))
        assert "count" in response
        assert response["count"] == 3
        assert len(response["tools"]) == 3

    def test_router_direct_call_endpoint(self, test_server):
        router = create_mcp_router(server=test_server)
        call_endpoint = next(r.endpoint for r in router.routes if r.path == "/api/v1/mcp/tools/call" and "POST" in r.methods)

        payload = DirectToolCallRequest(
            name="add_numbers",
            arguments={"a": 100, "b": 250},
        )
        result: CallToolResult = run_coroutine(call_endpoint(payload=payload, _auth="authorized_key"))
        assert result.isError is False
        assert result.content[0].text == "350"

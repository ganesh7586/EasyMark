"""
Core Model Context Protocol (MCP) Server Implementation.

Implements the official JSON-RPC 2.0 protocol specifications for:
- initialize / initialized handshake
- ping
- tools/list (Tool Discovery & Schema Reflection)
- tools/call (Tool Execution & Output Content Blocks)
"""

import json
from typing import Any, Dict, Optional, Union

from app.mcp_server.models import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    CallToolResult,
    InitializeResult,
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
    ServerCapabilities,
    ServerInfo,
)
from app.mcp_server.registry import ToolRegistry, default_registry

# Ensure built-in diagnostic tools and enterprise tools are registered upon server import
import app.mcp_server.diagnostic_tools  # noqa: F401
import app.mcp_server.tools.jira_tool  # noqa: F401
import app.mcp_server.tools.notion_tool  # noqa: F401
import app.mcp_server.tools.gmail_tool  # noqa: F401


class MCPServer:
    """
    Standard Model Context Protocol (MCP) Server engine.
    Orchestrates JSON-RPC 2.0 dispatch and tool execution.
    """

    def __init__(
        self,
        name: str = "company-intelligence-mcp-server",
        version: str = "1.0.0",
        registry: Optional[ToolRegistry] = None,
    ):
        self.server_info = ServerInfo(name=name, version=version)
        self.registry = registry or default_registry
        self.initialized = False

    async def handle_message(
        self,
        raw_message: Union[str, Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single JSON-RPC 2.0 message and generate the protocol response.

        Args:
            raw_message: Raw JSON string or dictionary payload.

        Returns:
            Dictionary response matching JSON-RPC 2.0, or None if the request was a notification.
        """
        # Step 1: Parse JSON if string
        if isinstance(raw_message, str):
            try:
                payload = json.loads(raw_message)
            except json.JSONDecodeError as err:
                return JSONRPCResponse(
                    id=None,
                    error=JSONRPCError(
                        code=PARSE_ERROR,
                        message=f"Parse error: {str(err)}",
                    ),
                ).model_dump(exclude_none=True)
        elif isinstance(raw_message, dict):
            payload = raw_message
        else:
            return JSONRPCResponse(
                id=None,
                error=JSONRPCError(
                    code=INVALID_REQUEST,
                    message="Invalid request: Payload must be a JSON object or string.",
                ),
            ).model_dump(exclude_none=True)

        # Step 2: Validate JSON-RPC 2.0 structure
        if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0" or "method" not in payload:
            req_id = payload.get("id") if isinstance(payload, dict) else None
            return JSONRPCResponse(
                id=req_id,
                error=JSONRPCError(
                    code=INVALID_REQUEST,
                    message="Invalid request: Missing required 'jsonrpc': '2.0' or 'method' field.",
                ),
            ).model_dump(exclude_none=True)

        method = payload.get("method", "")
        req_id = payload.get("id")
        params = payload.get("params") or {}
        is_notification = req_id is None

        # Step 3: Route JSON-RPC Method
        try:
            if method == "initialize":
                result = self._handle_initialize(params)
                self.initialized = True
                return JSONRPCResponse(id=req_id, result=result).model_dump(exclude_none=True)

            elif method in ("notifications/initialized", "initialized"):
                self.initialized = True
                # Notifications do not return a response according to JSON-RPC 2.0
                return None

            elif method == "ping":
                return JSONRPCResponse(id=req_id, result={}).model_dump(exclude_none=True)

            elif method == "tools/list":
                tools = [t.model_dump() for t in self.registry.list_tools()]
                return JSONRPCResponse(id=req_id, result={"tools": tools}).model_dump(exclude_none=True)

            elif method == "tools/call":
                if not isinstance(params, dict) or "name" not in params:
                    return JSONRPCResponse(
                        id=req_id,
                        error=JSONRPCError(
                            code=INVALID_PARAMS,
                            message="Invalid params: 'name' is required for 'tools/call'.",
                        ),
                    ).model_dump(exclude_none=True)

                tool_name = params["name"]
                tool_args = params.get("arguments", {})
                call_result: CallToolResult = await self.registry.execute_tool(tool_name, tool_args)
                return JSONRPCResponse(id=req_id, result=call_result.model_dump()).model_dump(exclude_none=True)

            else:
                if is_notification:
                    return None
                return JSONRPCResponse(
                    id=req_id,
                    error=JSONRPCError(
                        code=METHOD_NOT_FOUND,
                        message=f"Method not found: '{method}' is not implemented on this MCP server.",
                    ),
                ).model_dump(exclude_none=True)

        except Exception as exc:
            if is_notification:
                return None
            return JSONRPCResponse(
                id=req_id,
                error=JSONRPCError(
                    code=INTERNAL_ERROR,
                    message=f"Internal error: {str(exc)}",
                ),
            ).model_dump(exclude_none=True)

    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle protocol version negotiation and capability handshake."""
        result = InitializeResult(
            serverInfo=self.server_info,
            capabilities=ServerCapabilities(
                tools={"listChanged": False},
            ),
        )
        return result.model_dump()

    def handle_message_sync(
        self,
        raw_message: Union[str, Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for message handling."""
        coro = self.handle_message(raw_message)
        try:
            coro.send(None)
        except StopIteration as exc:
            return exc.value
        except Exception:
            import asyncio
            return asyncio.run(coro)


# Default server singleton
_default_server: Optional[MCPServer] = None


def get_mcp_server() -> MCPServer:
    """Accessor for the global MCP server instance."""
    global _default_server
    if _default_server is None:
        _default_server = MCPServer()
    return _default_server

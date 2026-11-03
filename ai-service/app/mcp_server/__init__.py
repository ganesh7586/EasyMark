"""
Model Context Protocol (MCP) Server Package.

Provides tool registration, JSON-RPC 2.0 protocol dispatch,
and multi-transport support (stdio, HTTP, SSE) for enterprise AI tools.
"""

from app.mcp_server.models import (
    CallToolResult,
    ContentBlock,
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
    ToolDefinition,
    ToolInputSchema,
)
from app.mcp_server.registry import (
    MCPTool,
    ToolRegistry,
    default_registry,
    mcp_tool,
)
from app.mcp_server.server import MCPServer, get_mcp_server
from app.mcp_server.transport import StdioTransport, create_mcp_router

__all__ = [
    "CallToolResult",
    "ContentBlock",
    "JSONRPCError",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "MCPTool",
    "MCPServer",
    "StdioTransport",
    "ToolDefinition",
    "ToolInputSchema",
    "ToolRegistry",
    "create_mcp_router",
    "default_registry",
    "get_mcp_server",
    "mcp_tool",
]

"""
Data models for Model Context Protocol (MCP) and JSON-RPC 2.0 specification.
Implements official MCP specifications for tool discovery and execution.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

# MCP Protocol Version standard
MCP_PROTOCOL_VERSION = "2024-11-05"
JSONRPC_VERSION = "2.0"

# Standard JSON-RPC 2.0 Error Codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class JSONRPCError(BaseModel):
    """Standard JSON-RPC 2.0 error object."""
    code: int
    message: str
    data: Optional[Any] = None


class JSONRPCRequest(BaseModel):
    """Standard JSON-RPC 2.0 request object."""
    jsonrpc: str = Field(default=JSONRPC_VERSION)
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class JSONRPCResponse(BaseModel):
    """Standard JSON-RPC 2.0 response object."""
    jsonrpc: str = Field(default=JSONRPC_VERSION)
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None


class ServerInfo(BaseModel):
    """Server metadata returned during MCP initialize handshake."""
    name: str = "company-intelligence-mcp-server"
    version: str = "1.0.0"


class ServerCapabilities(BaseModel):
    """Capabilities advertised by this MCP server."""
    tools: Dict[str, Any] = Field(default_factory=lambda: {"listChanged": False})
    resources: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None


class InitializeResult(BaseModel):
    """Result returned in response to the MCP 'initialize' method."""
    protocolVersion: str = MCP_PROTOCOL_VERSION
    capabilities: ServerCapabilities = Field(default_factory=ServerCapabilities)
    serverInfo: ServerInfo = Field(default_factory=ServerInfo)


class ToolInputSchema(BaseModel):
    """JSON Schema definition describing the expected arguments for an MCP tool."""
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class ToolDefinition(BaseModel):
    """Exposes a callable tool's metadata and JSON schema to the AI model."""
    name: str
    description: str
    inputSchema: ToolInputSchema


class ContentBlock(BaseModel):
    """Standard MCP content block (text or image) returned from a tool execution."""
    type: str = "text"
    text: str


class CallToolResult(BaseModel):
    """Result payload returned in response to 'tools/call'."""
    content: List[ContentBlock] = Field(default_factory=list)
    isError: bool = False

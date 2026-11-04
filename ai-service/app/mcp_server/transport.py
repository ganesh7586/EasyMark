"""
Transport Layer for Model Context Protocol (MCP) Server.

Provides dual transport mechanisms:
1. Standard Input/Output (stdio) for local subprocess and CLI execution (Claude Desktop, Cursor, subagent CLI).
2. HTTP / REST & Server-Sent Events (SSE) for integration into the FastAPI web gateway.
"""

import asyncio
import json
import sys
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.security import verify_internal_key
from app.mcp_server.models import CallToolResult, ToolDefinition
from app.mcp_server.server import MCPServer, get_mcp_server


class StdioTransport:
    """Manages MCP JSON-RPC communication over standard I/O (stdin / stdout)."""

    def __init__(self, server: Optional[MCPServer] = None):
        self.server = server or get_mcp_server()

    async def run(self):
        """Continuously read line-delimited JSON-RPC from stdin and write to stdout."""
        # Ensure utf-8 output
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")

        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            line_bytes = await reader.readline()
            if not line_bytes:
                break

            line_str = line_bytes.decode("utf-8").strip()
            if not line_str:
                continue

            response = await self.server.handle_message(line_str)
            if response is not None:
                output = json.dumps(response) + "\n"
                sys.stdout.write(output)
                sys.stdout.flush()


# --- FastAPI HTTP / SSE Router ---

class DirectToolCallRequest(BaseModel):
    name: str = Field(..., description="Target MCP tool name")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments dictionary matching tool schema")


def create_mcp_router(server: Optional[MCPServer] = None) -> APIRouter:
    """Creates a FastAPI router exposing the MCP server over HTTP and SSE."""
    mcp_server = server or get_mcp_server()
    router = APIRouter(prefix="/api/v1/mcp", tags=["Model Context Protocol (MCP)"])

    @router.post(
        "/message",
        summary="MCP JSON-RPC 2.0 Message Endpoint",
        description="Core MCP endpoint handling JSON-RPC requests (initialize, ping, tools/list, tools/call).",
    )
    async def handle_jsonrpc(
        payload: Dict[str, Any],
        _auth: str = Depends(verify_internal_key),
    ):
        response = await mcp_server.handle_message(payload)
        if response is None:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        return response

    @router.get(
        "/tools",
        summary="List Registered MCP Tools",
        description="Inspect all active tools and their generated JSON Schema parameter specifications.",
    )
    async def list_tools(
        _auth: str = Depends(verify_internal_key),
    ):
        tools = mcp_server.registry.list_tools()
        return {
            "count": len(tools),
            "tools": [t.model_dump() for t in tools],
        }

    @router.get(
        "/schema",
        summary="OpenAI / Groq LLM Function Calling Schema",
        description="Returns all registered MCP tools transformed into standard OpenAI / Groq tool specification format for agent function calling.",
    )
    async def get_openai_function_schema(
        _auth: str = Depends(verify_internal_key),
    ):
        from app.mcp_server.aggregator import get_mcp_aggregator
        aggregator = get_mcp_aggregator()
        specs = aggregator.to_openai_function_specs()
        return {
            "count": len(specs),
            "tools": specs,
        }

    @router.get(
        "/categories",
        summary="List Tools by Category",
        description="Inspect tool breakdown categorized by domain (jira, notion, gmail, diagnostic).",
    )
    async def get_tools_by_category(
        _auth: str = Depends(verify_internal_key),
    ):
        from app.mcp_server.aggregator import get_mcp_aggregator
        aggregator = get_mcp_aggregator()
        summaries = aggregator.get_tool_summaries()
        breakdown: Dict[str, list] = {"jira": [], "notion": [], "gmail": [], "diagnostic": []}
        for s in summaries:
            breakdown.setdefault(s.category, []).append({
                "name": s.name,
                "description": s.description,
                "required_parameters": s.required_parameters,
            })
        return breakdown

    @router.post(
        "/tools/call",
        response_model=CallToolResult,
        summary="Execute MCP Tool Directly",
        description="Convenience REST endpoint to execute a registered tool without manual JSON-RPC envelope packaging.",
    )
    async def call_tool_direct(
        payload: DirectToolCallRequest,
        _auth: str = Depends(verify_internal_key),
    ):
        result = await mcp_server.registry.execute_tool(
            name=payload.name,
            arguments=payload.arguments,
        )
        return result

    @router.get(
        "/sse",
        summary="MCP Server-Sent Events (SSE) Stream",
        description="Establishes an SSE event channel for real-time tool event streaming.",
    )
    async def mcp_sse(request: Request, _auth: str = Depends(verify_internal_key)):
        async def event_generator():
            # Initial handshake notification
            yield f"event: endpoint\ndata: /api/v1/mcp/message\n\n"
            yield f"event: message\ndata: {json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    return router

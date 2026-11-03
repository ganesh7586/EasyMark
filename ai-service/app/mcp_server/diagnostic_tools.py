"""
Built-in Diagnostic and Health Tools for Model Context Protocol (MCP) server.
Provides baseline verification of JSON-RPC schema reflection and execution.
"""

from datetime import datetime, timezone
import platform
import sys
from typing import Any, Dict

from app.core.config import settings
from app.mcp_server.registry import mcp_tool


@mcp_tool(
    name="system_health",
    description="Check the AI service and MCP server operational health, uptime, and system metadata.",
)
def system_health(detailed: bool = False) -> Dict[str, Any]:
    """
    Returns operational health status and server diagnostics.

    Args:
        detailed: If True, includes detailed environment and runtime metrics.
    """
    from app.mcp_server.registry import default_registry

    info: Dict[str, Any] = {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "registered_mcp_tools": len(default_registry.list_tools()),
    }

    if detailed:
        info["system"] = {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "environment": settings.ENVIRONMENT,
        }

    return info


@mcp_tool(
    name="echo_message",
    description="Echo a message back to verify argument serialization and parameter parsing.",
)
def echo_message(message: str, uppercase: bool = False) -> str:
    """
    Diagnostic echo tool.

    Args:
        message: The input text to echo.
        uppercase: If True, converts the output to uppercase.
    """
    if uppercase:
        return message.upper()
    return message


@mcp_tool(
    name="ping",
    description="Quick liveness ping returning 'pong'.",
)
def ping() -> str:
    """Ping probe."""
    return "pong"

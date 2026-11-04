"""
Unified MCP Client and Tool Aggregator Engine.

Aggregates all registered enterprise tools (Jira, Notion, Gmail, Diagnostics)
into a unified execution and schema-reflection client. Formats tool schemas
for direct ingestion by Groq / OpenAI LLM function calling and LangGraph nodes.
"""

from dataclasses import dataclass
import time
from typing import Any, Callable, Dict, List, Optional

from app.mcp_server.models import CallToolResult, ToolDefinition
from app.mcp_server.registry import ToolRegistry, default_registry
from app.mcp_server.server import MCPServer, get_mcp_server


@dataclass
class AggregatedToolSummary:
    """Summary of a tool's capabilities and its source domain."""
    name: str
    category: str
    description: str
    parameter_count: int
    required_parameters: List[str]


class UnifiedMCPAggregator:
    """
    Central coordinator aggregating all enterprise MCP tools into a unified interface.
    Provides schema reflection for LLM function calling and multi-tool execution.
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or default_registry

    def list_all_tools(self) -> List[ToolDefinition]:
        """Return all registered tools across all categories."""
        return self.registry.list_tools()

    def get_tool_category(self, tool_name: str) -> str:
        """Categorize a tool based on its prefix or domain."""
        if tool_name.startswith("jira_"):
            return "jira"
        elif tool_name.startswith("notion_"):
            return "notion"
        elif tool_name.startswith("gmail_"):
            return "gmail"
        else:
            return "diagnostic"

    def get_tools_by_category(self, category: str) -> List[ToolDefinition]:
        """Filter tools by domain category ('jira', 'notion', 'gmail', 'diagnostic')."""
        target_cat = category.strip().lower()
        return [
            t for t in self.list_all_tools()
            if self.get_tool_category(t.name) == target_cat
        ]

    def get_tool_summaries(self) -> List[AggregatedToolSummary]:
        """Generate structured summaries for all registered tools."""
        summaries = []
        for t in self.list_all_tools():
            summaries.append(
                AggregatedToolSummary(
                    name=t.name,
                    category=self.get_tool_category(t.name),
                    description=t.description,
                    parameter_count=len(t.inputSchema.properties),
                    required_parameters=t.inputSchema.required,
                )
            )
        return summaries

    def to_openai_function_specs(self) -> List[Dict[str, Any]]:
        """
        Convert all registered MCP tools into OpenAI / Groq compatible function specs.
        Ready for immediate injection into chat completion payloads.
        """
        specs = []
        for tool in self.list_all_tools():
            specs.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": tool.inputSchema.type,
                        "properties": tool.inputSchema.properties,
                        "required": tool.inputSchema.required,
                    },
                },
            })
        return specs

    def find_relevant_tools(self, query: str) -> List[ToolDefinition]:
        """
        Heuristic tool discovery matching user questions to the most relevant tools.

        Args:
            query: User's natural language question.

        Returns:
            List of candidate tools.
        """
        clean_q = query.strip().lower()
        matched = []

        keywords_map = {
            "jira": ["jira", "ticket", "sprint", "issue", "bug", "blocker", "task", "assignee", "sev-1", "sev-2"],
            "notion": ["notion", "meeting", "note", "spec", "prd", "action item", "doc", "post-mortem", "architecture"],
            "gmail": ["gmail", "email", "inbox", "escalation", "customer", "message", "approval", "thread"],
            "diagnostic": ["health", "status", "ping", "echo", "uptime"],
        }

        matched_categories = set()
        for cat, keywords in keywords_map.items():
            if any(k in clean_q for k in keywords):
                matched_categories.add(cat)

        if not matched_categories:
            # Return all tools if no specific category matched
            return self.list_all_tools()

        for cat in matched_categories:
            matched.extend(self.get_tools_by_category(cat))

        return matched

    async def execute_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute any registered tool with performance and latency tracking.

        Args:
            name: Tool name.
            arguments: Dictionary of arguments.

        Returns:
            Structured dictionary with result, latency_ms, and execution metadata.
        """
        start_time = time.time()
        result: CallToolResult = await self.registry.execute_tool(name=name, arguments=arguments)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "tool_name": name,
            "category": self.get_tool_category(name),
            "arguments": arguments or {},
            "is_error": result.isError,
            "content": [b.model_dump() for b in result.content],
            "latency_ms": duration_ms,
        }

    def execute_tool_sync(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for tool execution."""
        coro = self.execute_tool(name=name, arguments=arguments)
        try:
            coro.send(None)
        except StopIteration as exc:
            return exc.value
        except Exception:
            import asyncio
            return asyncio.run(coro)


# Global aggregator singleton
_default_aggregator: Optional[UnifiedMCPAggregator] = None


def get_mcp_aggregator() -> UnifiedMCPAggregator:
    """Accessor for the global MCP aggregator."""
    global _default_aggregator
    if _default_aggregator is None:
        _default_aggregator = UnifiedMCPAggregator()
    return _default_aggregator

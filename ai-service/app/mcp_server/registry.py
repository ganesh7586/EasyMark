"""
MCP Tool Registry and Dynamic Schema Reflection Engine.

Allows enterprise tools (Jira, Notion, Gmail) to be registered via clean decorators
and automatically generates JSON Schema parameter definitions for LLM tool selection.
"""

import asyncio
from dataclasses import dataclass
import inspect
from typing import Any, Callable, Dict, List, Optional, Union, get_type_hints

from app.mcp_server.models import (
    CallToolResult,
    ContentBlock,
    ToolDefinition,
    ToolInputSchema,
)

# Mapping Python types to standard JSON Schema types
TYPE_MAPPING = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _infer_json_schema(func: Callable[..., Any]) -> ToolInputSchema:
    """
    Introspects a Python callable to construct a valid JSON Schema object
    describing its expected parameters and required arguments.
    """
    sig = inspect.signature(func)
    type_hints = {}
    try:
        type_hints = get_type_hints(func)
    except Exception:
        pass

    properties: Dict[str, Any] = {}
    required: List[str] = []

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue

        param_type = type_hints.get(param_name, param.annotation)
        schema_type = "string"  # default fallback

        if param_type in TYPE_MAPPING:
            schema_type = TYPE_MAPPING[param_type]
        elif hasattr(param_type, "__origin__"):
            # Handle typing generics like List[str], Dict[str, Any], Optional[str]
            origin = param_type.__origin__
            if origin is list:
                schema_type = "array"
            elif origin is dict:
                schema_type = "object"
            elif origin is Union:
                # e.g., Optional[str] -> Union[str, NoneType]
                args = [a for a in param_type.__args__ if a is not type(None)]
                if args and args[0] in TYPE_MAPPING:
                    schema_type = TYPE_MAPPING[args[0]]

        prop_spec: Dict[str, Any] = {"type": schema_type}

        # Check if parameter has a default value
        if param.default is inspect.Parameter.empty:
            required.append(param_name)
        else:
            prop_spec["default"] = param.default

        properties[param_name] = prop_spec

    return ToolInputSchema(
        type="object",
        properties=properties,
        required=required,
    )


@dataclass
class MCPTool:
    """Metadata container for a registered MCP Tool."""
    name: str
    description: str
    func: Callable[..., Any]
    input_schema: ToolInputSchema
    is_async: bool


class ToolRegistry:
    """Manages the registration, inspection, and execution of MCP tools."""

    def __init__(self):
        self._tools: Dict[str, MCPTool] = {}

    def register(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        input_schema: Optional[ToolInputSchema] = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator to register a function as an MCP tool.

        Args:
            name: Custom tool name (defaults to function.__name__).
            description: Description of what the tool does (defaults to docstring).
            input_schema: Optional manual schema override.
        """
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or func.__name__
            tool_desc = description or (func.__doc__ or "").strip() or f"Execute {tool_name}"
            schema = input_schema or _infer_json_schema(func)
            is_async = inspect.iscoroutinefunction(func)

            tool_entry = MCPTool(
                name=tool_name,
                description=tool_desc,
                func=func,
                input_schema=schema,
                is_async=is_async,
            )
            self._tools[tool_name] = tool_entry
            return func

        return decorator

    def list_tools(self) -> List[ToolDefinition]:
        """Returns all registered tools in MCP standard format."""
        return [
            ToolDefinition(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.input_schema,
            )
            for tool in self._tools.values()
        ]

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Retrieve tool metadata by name."""
        return self._tools.get(name)

    async def execute_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> CallToolResult:
        """
        Executes a registered tool by name with provided arguments.

        Returns standard MCP CallToolResult.
        """
        tool = self.get_tool(name)
        if not tool:
            return CallToolResult(
                content=[ContentBlock(type="text", text=f"Error: Unknown tool '{name}'.")],
                isError=True,
            )

        args = arguments or {}

        # Validate required arguments
        for req in tool.input_schema.required:
            if req not in args:
                return CallToolResult(
                    content=[
                        ContentBlock(
                            type="text",
                            text=f"Error: Missing required argument '{req}' for tool '{name}'.",
                        )
                    ],
                    isError=True,
                )

        try:
            if tool.is_async:
                raw_result = await tool.func(**args)
            else:
                raw_result = tool.func(**args)

            # Format raw result to text
            if isinstance(raw_result, (dict, list)):
                import json
                text_content = json.dumps(raw_result, indent=2, default=str)
            else:
                text_content = str(raw_result)

            return CallToolResult(
                content=[ContentBlock(type="text", text=text_content)],
                isError=False,
            )
        except Exception as exc:
            return CallToolResult(
                content=[ContentBlock(type="text", text=f"Tool execution failed: {str(exc)}")],
                isError=True,
            )


# Global default registry
default_registry = ToolRegistry()
mcp_tool = default_registry.register

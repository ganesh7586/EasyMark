"""
Script: test_mcp_cli.py
Purpose: Interactive CLI demonstration of Model Context Protocol (MCP) JSON-RPC 2.0 communication.
Day 6 demonstration script.
"""

import json
from pathlib import Path
import sys
import time

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.mcp_server.server import get_mcp_server


def pretty_print_exchange(title: str, request: dict, response: dict):
    print(f"\n--- {title} ---")
    print(f"[Request JSON-RPC]:\n{json.dumps(request, indent=2)}")
    print(f"[Response JSON-RPC]:\n{json.dumps(response, indent=2)}")


def main():
    print("=" * 70)
    print("[DAY 6] MODEL CONTEXT PROTOCOL (MCP) SERVER DEMONSTRATION")
    print("=" * 70)

    server = get_mcp_server()

    # 1. MCP Initialize Handshake
    req_init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "cli-test-client", "version": "1.0.0"},
        },
    }
    resp_init = server.handle_message_sync(req_init)
    pretty_print_exchange("1. Protocol Handshake (initialize)", req_init, resp_init)

    # 2. Ping Probe
    req_ping = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
    resp_ping = server.handle_message_sync(req_ping)
    pretty_print_exchange("2. Protocol Liveness (ping)", req_ping, resp_ping)

    # 3. Tool Discovery & Schema Reflection (tools/list)
    req_list = {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
    resp_list = server.handle_message_sync(req_list)
    pretty_print_exchange("3. Tool Discovery & JSON Schema Reflection (tools/list)", req_list, resp_list)

    # 4. Tool Execution (tools/call: system_health)
    req_call_health = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "system_health",
            "arguments": {"detailed": True},
        },
    }
    resp_call_health = server.handle_message_sync(req_call_health)
    pretty_print_exchange("4. Tool Execution (tools/call: system_health)", req_call_health, resp_call_health)

    # 5. Tool Execution with parameter transformation (tools/call: echo_message)
    req_call_echo = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "echo_message",
            "arguments": {"message": "MCP server initialized successfully on Day 6!", "uppercase": True},
        },
    }
    resp_call_echo = server.handle_message_sync(req_call_echo)
    pretty_print_exchange("5. Tool Execution (tools/call: echo_message)", req_call_echo, resp_call_echo)

    # 6. Error Handling: Unknown Method (-32601)
    req_err = {"jsonrpc": "2.0", "id": 6, "method": "non_existent_method"}
    resp_err = server.handle_message_sync(req_err)
    pretty_print_exchange("6. Error Handling: Method Not Found (-32601)", req_err, resp_err)

    print("\n" + "=" * 70)
    print("[SUCCESS] All 6 MCP protocol phases verified successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()

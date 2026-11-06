"""
LangGraph State Machine Engine for Company Intelligence AI.
Defines graph nodes, conditional routing edges, and compiled workflow execution.
"""

import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel

from app.agent.state import AgentState
from app.agent.evaluator import evaluate_query_node
from app.agent.validator import evaluate_evidence_node
from app.rag.rag_service import StaticRAGService
from app.mcp_server.aggregator import UnifiedMCPAggregator


# Constants representing graph boundaries
START = "__start__"
END = "__end__"


class StateGraph:
    """
    StateGraph Builder compatible with LangGraph design patterns.
    Provides node registration, conditional edges, and execution compiling.
    """

    def __init__(self, state_schema=AgentState):
        self.state_schema = state_schema
        self.nodes: Dict[str, Callable[[AgentState], AgentState]] = {}
        self.edges: Dict[str, str] = {}
        self.conditional_edges: Dict[str, Tuple[Callable[[AgentState], str], Dict[str, str]]] = {}
        self.entry_point: Optional[str] = None

    def add_node(self, name: str, action: Callable[[AgentState], AgentState]) -> "StateGraph":
        """Registers a named action node in the graph."""
        self.nodes[name] = action
        return self

    def set_entry_point(self, name: str) -> "StateGraph":
        """Designates the first node to execute after START."""
        self.entry_point = name
        return self

    def add_edge(self, start_node: str, end_node: str) -> "StateGraph":
        """Adds a direct deterministic transition edge between two nodes."""
        self.edges[start_node] = end_node
        return self

    def add_conditional_edges(
        self,
        source_node: str,
        path: Callable[[AgentState], str],
        path_map: Dict[str, str],
    ) -> "StateGraph":
        """Adds a conditional branch routing to different target nodes based on state."""
        self.conditional_edges[source_node] = (path, path_map)
        return self

    def compile(self) -> "CompiledStateGraph":
        """Validates and compiles the graph into an executable state machine."""
        if not self.entry_point:
            raise ValueError("StateGraph requires an entry point. Call set_entry_point() before compiling.")
        return CompiledStateGraph(
            nodes=self.nodes,
            edges=self.edges,
            conditional_edges=self.conditional_edges,
            entry_point=self.entry_point,
        )


class CompiledStateGraph:
    """
    Executable compiled state graph machine.
    Drives state step-by-step through registered nodes until END is reached.
    """

    def __init__(
        self,
        nodes: Dict[str, Callable[[AgentState], AgentState]],
        edges: Dict[str, str],
        conditional_edges: Dict[str, Tuple[Callable[[AgentState], str], Dict[str, str]]],
        entry_point: str,
    ):
        self.nodes = nodes
        self.edges = edges
        self.conditional_edges = conditional_edges
        self.entry_point = entry_point

    def invoke(self, state: AgentState) -> AgentState:
        """
        Executes the state machine synchronously from entry point to END.
        """
        start_overall = time.time()
        current_node = self.entry_point
        max_steps = 25
        step_count = 0

        while current_node and current_node != END and step_count < max_steps:
            step_count += 1
            if current_node not in self.nodes:
                raise KeyError(f"Node '{current_node}' is not registered in the state graph.")

            # Execute current node action
            node_fn = self.nodes[current_node]
            state = node_fn(state)

            # Determine next node via conditional edges or standard edges
            if current_node in self.conditional_edges:
                condition_fn, path_map = self.conditional_edges[current_node]
                decision_key = condition_fn(state)
                next_node = path_map.get(decision_key, END)
            elif current_node in self.edges:
                next_node = self.edges[current_node]
            else:
                next_node = END

            current_node = next_node

        state.latency_ms = round((time.time() - start_overall) * 1000, 2)
        return state


# =========================================================================
# Graph Node Implementations
# =========================================================================

_rag_service_instance: Optional[StaticRAGService] = None
_mcp_aggregator_instance: Optional[UnifiedMCPAggregator] = None


def get_rag_service() -> StaticRAGService:
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = StaticRAGService()
    return _rag_service_instance


def get_mcp_aggregator() -> UnifiedMCPAggregator:
    global _mcp_aggregator_instance
    if _mcp_aggregator_instance is None:
        _mcp_aggregator_instance = UnifiedMCPAggregator()
    return _mcp_aggregator_instance


def static_rag_node(state: AgentState) -> AgentState:
    """
    Node: Queries Static PDF RAG Service for authoritative company policies.
    """
    start_time = time.time()
    rag = get_rag_service()
    result = rag.query(
        query_text=state.query,
        top_k=4,
        doc_filter=state.doc_filter,
    )

    state.rag_result = {
        "answer": result.answer,
        "citations": result.citations,
        "sources_used": result.sources_used,
        "retrieved_chunks_count": result.retrieved_chunks_count,
        "latency_ms": result.latency_ms,
        "model": result.model,
    }
    state.citations.extend(result.citations)
    for src in result.sources_used:
        if src not in state.sources_used:
            state.sources_used.append(src)

    duration = (time.time() - start_time) * 1000
    state.log_node_execution(
        node_name="execute_static_rag",
        duration_ms=duration,
        details={
            "retrieved_chunks": result.retrieved_chunks_count,
            "citations_found": len(result.citations),
            "sources": result.sources_used,
        },
    )
    return state


def mcp_tools_node(state: AgentState) -> AgentState:
    """
    Node: Executes target Live MCP Tools across Jira, Notion, and Gmail.
    """
    start_time = time.time()
    aggregator = get_mcp_aggregator()
    tools_to_run = state.target_tools or ["jira_get_blockers"]

    for tool_name in tools_to_run:
        # Prepare arguments based on extracted entities
        args: Dict[str, Any] = {}
        if tool_name == "jira_get_blockers":
            args = {"project_key": "ALPHA"}
        elif tool_name == "jira_get_sprint_issues":
            args = {"project_key": "ALPHA"}
        elif tool_name == "jira_get_issue_details":
            issue_key = state.extracted_entities.get("jira_issues", ["ALPHA-101"])[0]
            args = {"issue_key": issue_key}
        elif tool_name == "notion_get_page":
            notion_id = state.extracted_entities.get("notion_ids", ["NOTION-SPEC-01"])[0]
            args = {"page_id_or_title": notion_id}
        elif tool_name == "notion_get_meeting_notes":
            args = {"limit": 3}
        elif tool_name == "notion_get_action_items":
            args = {"status": "all"}
        elif tool_name == "gmail_get_customer_escalations":
            sev = state.extracted_entities.get("severities", ["SEV-1"])[0]
            args = {"severity": sev}
        elif tool_name == "gmail_check_pending_approvals":
            args = {}
        else:
            args = {}

        tool_exec = aggregator.execute_tool_sync(tool_name, args)
        state.mcp_results.append(tool_exec)

        # Record application sources
        app_name = f"MCP:{tool_exec.get('category', 'tool').upper()}"
        if app_name not in state.sources_used:
            state.sources_used.append(app_name)

    duration = (time.time() - start_time) * 1000
    state.log_node_execution(
        node_name="execute_mcp_tools",
        duration_ms=duration,
        details={
            "tools_executed": tools_to_run,
            "results_count": len(state.mcp_results),
        },
    )
    return state


def hybrid_node(state: AgentState) -> AgentState:
    """
    Node: Executes both Static RAG and MCP Tools for cross-domain synthesis.
    """
    start_time = time.time()
    # 1. Execute Static Policy Retrieval
    state = static_rag_node(state)
    # 2. Execute Live Application Data Retrieval
    state = mcp_tools_node(state)

    duration = (time.time() - start_time) * 1000
    state.log_node_execution(
        node_name="execute_hybrid_orchestrator",
        duration_ms=duration,
        details={"hybrid": True},
    )
    return state


def format_response_node(state: AgentState) -> AgentState:
    """
    Node: Synthesizes final grounded response and harmonizes citations.
    """
    start_time = time.time()

    # Fallback if evidence evaluation determined insufficient grounding
    if not state.evidence_valid and state.route != "direct_response":
        state.final_answer = (
            "The available company policy documents and workplace systems do not contain "
            "sufficient verified evidence to answer this question."
        )
    elif state.route == "direct_response":
        if state.intent == "greeting_or_general":
            state.final_answer = (
                "Hello! I am Company Intelligence AI, your enterprise knowledge assistant. "
                "I can answer questions regarding official company policies (HR rules, SLAs, Charter) "
                "and retrieve real-time operational data from Jira sprints, Notion specs, and Gmail customer escalations."
            )
        elif state.intent == "adversarial_trap" or state.intent == "out_of_domain":
            state.final_answer = (
                "The available company policy documents and workplace systems do not contain "
                "sufficient information to answer this question."
            )
        else:
            state.final_answer = (
                "The available company policy documents do not contain sufficient information to answer this question."
            )

    elif state.route == "static_rag" and state.rag_result:
        state.final_answer = state.rag_result.get("answer", "")

    elif state.route == "mcp_tools" and state.mcp_results:
        # Format live tool results cleanly
        import json
        formatted_blocks = []
        for res in state.mcp_results:
            t_name = res.get("tool_name", "tool")
            content = res.get("content", [])
            text_body = content[0].get("text", "") if content else ""
            formatted_blocks.append(f"### Live Data from `{t_name}`:\n```json\n{text_body}\n```")

        state.final_answer = (
            "Here is the real-time operational data retrieved from our live workplace systems:\n\n"
            + "\n\n".join(formatted_blocks)
        )

    elif state.route == "hybrid":
        rag_answer = state.rag_result.get("answer", "") if state.rag_result else ""
        import json
        mcp_blocks = []
        for res in state.mcp_results:
            t_name = res.get("tool_name", "tool")
            content = res.get("content", [])
            text_body = content[0].get("text", "") if content else ""
            mcp_blocks.append(f"**Live System (`{t_name}`):**\n```json\n{text_body}\n```")

        state.final_answer = (
            f"**Policy Specification:**\n{rag_answer}\n\n"
            f"**Operational Cross-Correlation:**\n"
            + "\n\n".join(mcp_blocks)
        )

    duration = (time.time() - start_time) * 1000
    state.log_node_execution(
        node_name="format_response",
        duration_ms=duration,
        details={"sources_used": state.sources_used},
    )
    return state


def route_decision_edge(state: AgentState) -> str:
    """
    Conditional Routing Edge: Maps evaluated state route to the next graph node.
    """
    if state.route == "static_rag":
        return "static_rag"
    elif state.route == "mcp_tools":
        return "mcp_tools"
    elif state.route == "hybrid":
        return "hybrid"
    else:
        return "direct_response"


def build_company_intelligence_graph() -> CompiledStateGraph:
    """
    Builds and compiles the complete multi-agent LangGraph workflow.
    Topology:
      evaluate_query -> [static_rag | mcp_tools | hybrid | direct_response]
                     -> evaluate_evidence -> format_response -> END
    """
    graph = StateGraph(state_schema=AgentState)

    # 1. Register Graph Nodes
    graph.add_node("evaluate_query", evaluate_query_node)
    graph.add_node("static_rag", static_rag_node)
    graph.add_node("mcp_tools", mcp_tools_node)
    graph.add_node("hybrid", hybrid_node)
    graph.add_node("evaluate_evidence", evaluate_evidence_node)
    graph.add_node("format_response", format_response_node)

    # 2. Set Entry Point
    graph.set_entry_point("evaluate_query")

    # 3. Add Conditional Routing Edges
    graph.add_conditional_edges(
        source_node="evaluate_query",
        path=route_decision_edge,
        path_map={
            "static_rag": "static_rag",
            "mcp_tools": "mcp_tools",
            "hybrid": "hybrid",
            "direct_response": "evaluate_evidence",
        },
    )

    # 4. Connect Domain Retrieval Nodes to Evidence Evaluator
    graph.add_edge("static_rag", "evaluate_evidence")
    graph.add_edge("mcp_tools", "evaluate_evidence")
    graph.add_edge("hybrid", "evaluate_evidence")

    # 5. Connect Evidence Evaluator to Response Formatter
    graph.add_edge("evaluate_evidence", "format_response")

    # 6. Connect Final Node to END
    graph.add_edge("format_response", END)

    return graph.compile()

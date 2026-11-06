"""
Agent State Definition for Company Intelligence AI.
Defines the typed schema for LangGraph state passing across all nodes.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    """
    Central state container passed across all LangGraph nodes.
    Maintains full execution history, routing decisions, evidence, and provenance.
    """

    # --- Input Fields ---
    query: str = Field(..., description="User's natural language question or request")
    thread_id: Optional[str] = Field(default=None, description="Conversation session or thread ID")
    user_id: Optional[str] = Field(default="employee_default", description="Identifier for querying user")

    # --- Evaluator & Routing Metadata ---
    intent: Optional[str] = Field(
        default=None,
        description="Classified user intent (e.g. static_policy, live_ops, hybrid, general)",
    )
    route: Optional[str] = Field(
        default=None,
        description="Target execution branch: 'static_rag', 'mcp_tools', 'hybrid', 'direct_response'",
    )
    confidence: float = Field(default=0.0, description="Routing decision confidence score (0.0 - 1.0)")
    reasoning: str = Field(default="", description="Chain-of-thought rationale for routing decision")
    extracted_entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted entities such as issue keys, doc names, severity levels, dates",
    )
    target_tools: List[str] = Field(
        default_factory=list,
        description="Identified MCP tool names required for resolving the query",
    )
    doc_filter: Optional[str] = Field(
        default=None,
        description="Optional PDF document filter for scoping Static RAG",
    )

    # --- Evidence & Retrieved Data ---
    rag_result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Output payload from Static PDF RAG search (answer, citations, chunks)",
    )
    mcp_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Results collected from executed MCP tools (Jira, Notion, Gmail)",
    )

    # --- Final Output & Observability ---
    final_answer: Optional[str] = Field(
        default=None,
        description="Synthesized grounded answer delivered to the user",
    )
    citations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of verified citations linking to PDFs or MCP live objects",
    )
    structured_citations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Enriched, validated citation objects with provenance metadata and deep references",
    )
    grounding_score: float = Field(
        default=0.0,
        description="Mathematical evidence grounding confidence score (0.0 to 1.0)",
    )
    evidence_valid: bool = Field(
        default=True,
        description="Whether the retrieved evidence is deemed sufficient and grounded",
    )
    evidence_summary: Optional[str] = Field(
        default=None,
        description="Concise summary assessment of evidence quality and provenance",
    )
    sources_used: List[str] = Field(
        default_factory=list,
        description="High-level list of source documents and applications consulted",
    )
    execution_trace: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Chronological audit log of graph node transitions and timing",
    )
    latency_ms: float = Field(default=0.0, description="End-to-end processing duration in milliseconds")
    error: Optional[str] = Field(default=None, description="Error message if any failure occurred")

    def log_node_execution(self, node_name: str, duration_ms: float, details: Optional[Dict[str, Any]] = None) -> None:
        """Appends an execution step to the state's audit trace."""
        self.execution_trace.append({
            "step": len(self.execution_trace) + 1,
            "node": node_name,
            "duration_ms": round(duration_ms, 2),
            "details": details or {},
        })

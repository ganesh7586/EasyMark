"""
FastAPI Routes for LangGraph Agent Orchestration.
Exposes /api/v1/agent/evaluate and /api/v1/agent/query endpoints.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.agent.orchestrator import get_agent_orchestrator, AgentOrchestrator
from app.core.security import verify_internal_key

router = APIRouter(prefix="/api/v1/agent", tags=["Agent Orchestrator"])


class AgentQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Employee question")
    thread_id: Optional[str] = Field(default=None, description="Optional conversation session ID")
    user_id: Optional[str] = Field(default="employee_default", description="User identifier")


class EvaluateQueryResponse(BaseModel):
    query: str
    intent: str
    route: str
    confidence: float
    reasoning: str
    target_tools: List[str]
    doc_filter: Optional[str]
    extracted_entities: Dict[str, Any]


class AgentQueryResponse(BaseModel):
    query: str
    resolved_query: Optional[str] = None
    thread_id: Optional[str]
    turn_index: int = 1
    intent: str
    route: str
    confidence: float
    grounding_score: float = 0.0
    evidence_valid: bool = True
    answer: str
    citations: List[Dict[str, Any]]
    structured_citations: List[Dict[str, Any]] = Field(default_factory=list)
    sources_used: List[str]
    execution_trace: List[Dict[str, Any]]
    latency_ms: float


class ThreadHistoryResponse(BaseModel):
    thread_id: str
    total_turns: int
    history: List[Dict[str, Any]]


class ThreadDeleteResponse(BaseModel):
    thread_id: str
    deleted_turns: int
    status: str


@router.post(
    "/evaluate",
    response_model=EvaluateQueryResponse,
    summary="Fast evaluation and intent routing of user query",
)
async def evaluate_query(
    payload: AgentQueryRequest,
    _authenticated: str = Depends(verify_internal_key),
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
):
    """
    Evaluates the intent of a query, extracting entities and determining the optimal
    routing path (Static RAG vs. MCP Live Tools vs. Cross-Domain Hybrid).
    """
    decision = orchestrator.evaluate_query(payload.query)
    return EvaluateQueryResponse(
        query=payload.query,
        intent=decision.intent,
        route=decision.route,
        confidence=decision.confidence,
        reasoning=decision.reasoning,
        target_tools=decision.target_tools,
        doc_filter=decision.doc_filter,
        extracted_entities=decision.extracted_entities,
    )


@router.post(
    "/query",
    response_model=AgentQueryResponse,
    summary="Full LangGraph Agent execution across Static RAG & Live MCP Tools",
)
async def execute_agent_query(
    payload: AgentQueryRequest,
    _authenticated: str = Depends(verify_internal_key),
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
):
    """
    Executes the full LangGraph state machine workflow for an incoming employee question.
    """
    state = orchestrator.process_query(
        query=payload.query,
        thread_id=payload.thread_id,
        user_id=payload.user_id,
    )

    return AgentQueryResponse(
        query=state.query,
        resolved_query=state.resolved_query,
        thread_id=state.thread_id,
        turn_index=state.turn_index,
        intent=state.intent or "unknown",
        route=state.route or "unknown",
        confidence=state.confidence,
        grounding_score=state.grounding_score,
        evidence_valid=state.evidence_valid,
        answer=state.final_answer or "",
        citations=state.citations,
        structured_citations=state.structured_citations,
        sources_used=state.sources_used,
        execution_trace=state.execution_trace,
        latency_ms=state.latency_ms,
    )


@router.get(
    "/threads/{thread_id}/history",
    response_model=ThreadHistoryResponse,
    summary="Retrieve multi-turn conversation checkpoints for a session thread",
)
async def get_thread_history(
    thread_id: str,
    limit: int = 20,
    _authenticated: str = Depends(verify_internal_key),
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
):
    """
    Returns full turn history and state checkpoints for a thread.
    """
    history = orchestrator.get_thread_history(thread_id, limit=limit)
    return ThreadHistoryResponse(
        thread_id=thread_id,
        total_turns=len(history),
        history=history,
    )


@router.delete(
    "/threads/{thread_id}",
    response_model=ThreadDeleteResponse,
    summary="Delete all checkpoints and clear memory for a session thread",
)
async def delete_thread(
    thread_id: str,
    _authenticated: str = Depends(verify_internal_key),
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
):
    """
    Clears all saved turns and entity memory for a thread.
    """
    deleted = orchestrator.clear_thread(thread_id)
    return ThreadDeleteResponse(
        thread_id=thread_id,
        deleted_turns=deleted,
        status="cleared",
    )

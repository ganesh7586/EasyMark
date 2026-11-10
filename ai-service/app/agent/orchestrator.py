"""
Agent Orchestrator Service.
High-level service interface for driving the LangGraph Question Evaluator,
Query Router, Multi-Agent workflow execution, and conversation memory persistence.
"""

from typing import Any, Dict, List, Optional
from app.agent.state import AgentState
from app.agent.evaluator import QuestionEvaluator, RoutingDecision
from app.agent.graph import build_company_intelligence_graph, CompiledStateGraph
from app.memory.manager import MemoryManager, get_memory_manager


class AgentOrchestrator:
    """
    Main orchestration entrypoint for the Company Intelligence Agent.
    Coordinates query intake, graph initialization, execution, memory retrieval,
    and state persistence.
    """

    def __init__(
        self,
        graph: Optional[CompiledStateGraph] = None,
        memory_manager: Optional[MemoryManager] = None,
    ):
        self.graph = graph or build_company_intelligence_graph()
        self.evaluator = QuestionEvaluator()
        self.memory = memory_manager or get_memory_manager()

    def evaluate_query(self, query: str) -> RoutingDecision:
        """
        Fast evaluation and classification without full multi-node graph execution.
        Used for diagnostics, routing preview, and API intent introspection.
        """
        return self.evaluator.evaluate(query)

    def process_query(
        self,
        query: str,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = "employee_default",
    ) -> AgentState:
        """
        Executes the full LangGraph state machine for a user query with multi-turn
        memory retrieval, coreference resolution, and MongoDB checkpointing.

        Args:
            query: Employee's natural language question.
            thread_id: Optional session/thread identifier.
            user_id: Identifier for audit and personalization.

        Returns:
            Final AgentState containing answer, citations, evidence, and execution trace.
        """
        clean_query = query.strip()
        uid = user_id or "employee_default"

        # 1. Load prior conversation context and accumulated entities from MongoDB
        turn_index, history, accumulated_entities = self.memory.load_thread_context(thread_id)

        # 2. Contextual Coreference Resolution (resolving "it", "that blocker", etc.)
        resolved_query = self.memory.resolve_coreferences(clean_query, accumulated_entities, history)
        has_resolution = resolved_query != clean_query

        # 3. Construct Initial AgentState with conversation memory
        initial_state = AgentState(
            query=clean_query,
            resolved_query=resolved_query if has_resolution else None,
            thread_id=thread_id,
            user_id=uid,
            turn_index=turn_index,
            conversation_history=history,
            accumulated_entities=accumulated_entities,
        )

        # 4. Invoke LangGraph multi-agent workflow
        final_state = self.graph.invoke(initial_state)

        # 5. Persist State Checkpoint into MongoDB (Day 13)
        if thread_id:
            self.memory.record_turn(thread_id, uid, final_state)

        return final_state

    def stream_query(
        self,
        query: str,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = "employee_default",
    ):
        """
        Yields Server-Sent Events (SSE) in real-time:
        - event: metadata
        - event: chunk
        - event: citations
        - event: trace
        - event: done
        """
        import json
        import time

        start_time = time.time()
        clean_query = query.strip()
        uid = user_id or "employee_default"

        # 1. Load context & resolve coreferences
        turn_index, history, accumulated_entities = self.memory.load_thread_context(thread_id)
        resolved_query = self.memory.resolve_coreferences(clean_query, accumulated_entities, history)
        has_resolution = resolved_query != clean_query

        # 2. Invoke state graph
        initial_state = AgentState(
            query=clean_query,
            resolved_query=resolved_query if has_resolution else None,
            thread_id=thread_id,
            user_id=uid,
            turn_index=turn_index,
            conversation_history=history,
            accumulated_entities=accumulated_entities,
        )
        final_state = self.graph.invoke(initial_state)

        # 3. Stream Metadata Event
        meta = {
            "query": clean_query,
            "resolved_query": final_state.resolved_query,
            "route": final_state.route or "direct_synthesis",
            "intent": final_state.intent,
            "confidence": final_state.confidence,
            "turn_index": final_state.turn_index,
            "thread_id": thread_id,
        }
        yield f"event: metadata\ndata: {json.dumps(meta)}\n\n"

        # 4. Stream Answer Chunks
        full_answer = final_state.final_answer or ""
        words = full_answer.split(" ")
        for i, word in enumerate(words):
            token = word + (" " if i < len(words) - 1 else "")
            yield f"event: chunk\ndata: {json.dumps({'token': token})}\n\n"

        # 5. Stream Citations Event
        cite_payload = {
            "citations": final_state.citations,
            "structured_citations": final_state.structured_citations,
            "grounding_score": final_state.grounding_score,
            "evidence_valid": final_state.evidence_valid,
        }
        yield f"event: citations\ndata: {json.dumps(cite_payload)}\n\n"

        # 6. Stream Execution Trace Event
        trace_payload = {
            "execution_trace": final_state.execution_trace,
        }
        yield f"event: trace\ndata: {json.dumps(trace_payload)}\n\n"

        # 7. Record checkpoint in MongoDB
        if thread_id:
            self.memory.record_turn(thread_id, uid, final_state)

        # 8. Stream Done Event
        latency = round((time.time() - start_time) * 1000, 2)
        yield f"event: done\ndata: {json.dumps({'latency_ms': latency, 'thread_id': thread_id})}\n\n"

    def get_thread_history(self, thread_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve full conversation turn history for a thread."""
        return self.memory.get_thread_history(thread_id, limit=limit)

    def clear_thread(self, thread_id: str) -> int:
        """Clear all conversation checkpoints and memory for a thread."""
        return self.memory.delete_thread(thread_id)


_agent_orchestrator_instance: Optional[AgentOrchestrator] = None


def get_agent_orchestrator() -> AgentOrchestrator:
    """Singleton factory for AgentOrchestrator."""
    global _agent_orchestrator_instance
    if _agent_orchestrator_instance is None:
        _agent_orchestrator_instance = AgentOrchestrator()
    return _agent_orchestrator_instance

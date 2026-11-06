"""
Agent Orchestrator Service.
High-level service interface for driving the LangGraph Question Evaluator,
Query Router, and Multi-Agent workflow execution.
"""

from typing import Any, Dict, Optional
from app.agent.state import AgentState
from app.agent.evaluator import QuestionEvaluator, RoutingDecision
from app.agent.graph import build_company_intelligence_graph, CompiledStateGraph


class AgentOrchestrator:
    """
    Main orchestration entrypoint for the Company Intelligence Agent.
    Coordinates query intake, graph initialization, execution, and state persistence.
    """

    def __init__(self, graph: Optional[CompiledStateGraph] = None):
        self.graph = graph or build_company_intelligence_graph()
        self.evaluator = QuestionEvaluator()

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
        Executes the full LangGraph state machine for a user query.

        Args:
            query: Employee's natural language question.
            thread_id: Optional session/thread identifier.
            user_id: Identifier for audit and personalization.

        Returns:
            Final AgentState containing answer, citations, evidence, and execution trace.
        """
        initial_state = AgentState(
            query=query.strip(),
            thread_id=thread_id,
            user_id=user_id,
        )

        final_state = self.graph.invoke(initial_state)
        return final_state


_agent_orchestrator_instance: Optional[AgentOrchestrator] = None


def get_agent_orchestrator() -> AgentOrchestrator:
    """Singleton factory for AgentOrchestrator."""
    global _agent_orchestrator_instance
    if _agent_orchestrator_instance is None:
        _agent_orchestrator_instance = AgentOrchestrator()
    return _agent_orchestrator_instance

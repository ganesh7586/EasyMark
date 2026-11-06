"""
Unit and Integration Tests for LangGraph Question Evaluator,
Query Router, and Agent Orchestrator (Day 11).
"""

from fastapi import HTTPException
import pytest

from app.agent.evaluator import QuestionEvaluator, evaluate_query_node
from app.agent.state import AgentState
from app.agent.graph import (
    StateGraph,
    START,
    END,
    build_company_intelligence_graph,
    route_decision_edge,
)
from app.agent.orchestrator import AgentOrchestrator
from app.api.agent import (
    AgentQueryRequest,
    AgentQueryResponse,
    EvaluateQueryResponse,
    evaluate_query,
    execute_agent_query,
)
from app.core.config import settings


def run_coroutine(coro):
    """Directly drives synchronous coroutines without spinning up socket-bound loops."""
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value


class TestQuestionEvaluator:
    """Tests for entity extraction, semantic intent classification, and routing decisions."""

    @pytest.fixture
    def evaluator(self):
        return QuestionEvaluator()

    def test_entity_extraction_jira_and_severity(self, evaluator):
        query = "What is the status of critical blocker ALPHA-101 and is it classified as SEV-1?"
        entities = evaluator.extract_entities(query)
        assert "jira_issues" in entities
        assert "ALPHA-101" in entities["jira_issues"]
        assert "severities" in entities
        assert "SEV-1" in entities["severities"]

    def test_entity_extraction_notion_and_doc(self, evaluator):
        query = "Check technical spec NOTION-SPEC-01 regarding our remote work policy rules."
        entities = evaluator.extract_entities(query)
        assert "notion_ids" in entities
        assert "NOTION-SPEC-01" in entities["notion_ids"]
        assert entities.get("likely_doc") == "Company_HR_and_Work_Rules.pdf"

    def test_route_static_policy_query(self, evaluator):
        queries = [
            "What are the core collaboration hours for remote employees?",
            "How many working days in advance must planned leave be submitted?",
            "What is the required initial response SLA for a SEV-1 outage?",
            "What are the deliverables and target dates for Milestone M2?",
        ]
        for q in queries:
            decision = evaluator.evaluate(q)
            assert decision.route == "static_rag", f"Failed for query: {q}"
            assert decision.confidence >= 0.85

    def test_route_live_jira_query(self, evaluator):
        queries = [
            "What are the active blocker tickets currently in the sprint?",
            "Show me all tickets assigned to Sarah in the current active sprint.",
            "Can you fetch details on Jira ticket ALPHA-102?",
        ]
        for q in queries:
            decision = evaluator.evaluate(q)
            assert decision.route == "mcp_tools", f"Failed for query: {q}"
            assert any(t.startswith("jira_") for t in decision.target_tools)

    def test_route_live_notion_query(self, evaluator):
        queries = [
            "Find the architecture specification for MongoDB vector search.",
            "What were the action items discussed in the last sprint retro sync?",
            "Retrieve page NOTION-NOTE-02 from Notion workspace.",
        ]
        for q in queries:
            decision = evaluator.evaluate(q)
            assert decision.route == "mcp_tools", f"Failed for query: {q}"
            assert any(t.startswith("notion_") for t in decision.target_tools)

    def test_route_live_gmail_query(self, evaluator):
        queries = [
            "Are there any customer escalation emails from Acme Corp?",
            "Check my inbox for pending deployment approvals and sign-offs.",
            "Show all SEV-1 customer escalation email threads.",
        ]
        for q in queries:
            decision = evaluator.evaluate(q)
            assert decision.route == "mcp_tools", f"Failed for query: {q}"
            assert any(t.startswith("gmail_") for t in decision.target_tools)

    def test_route_cross_domain_hybrid_query(self, evaluator):
        queries = [
            "Is the open blocker ticket ALPHA-101 violating our SEV-1 SLA response policy?",
            "Does our current sprint blocker comply with engineering SLA resolution rules?",
            "Compare the Acme Corp customer escalation against our official SLA response targets.",
        ]
        for q in queries:
            decision = evaluator.evaluate(q)
            assert decision.route == "hybrid", f"Failed for query: {q}"
            assert decision.intent == "cross_domain_hybrid"
            assert len(decision.target_tools) > 0

    def test_route_adversarial_trap_direct_response(self, evaluator):
        traps = [
            "Can I get reimbursed for a 500,000 INR Rolex watch?",
            "What is our corporate policy on bringing pet monkeys to the office?",
            "When can I take my 6-month paid sabbatical after 1 month of work?",
        ]
        for t in traps:
            decision = evaluator.evaluate(t)
            assert decision.route == "direct_response", f"Failed trap: {t}"
            assert decision.intent == "adversarial_trap"

    def test_route_out_of_domain_query(self, evaluator):
        distractors = [
            "What is the best sourdough bread baking recipe?",
            "Who won the 1998 FIFA World Cup?",
            "What is the distance from the Earth to the Moon in kilometers?",
        ]
        for d in distractors:
            decision = evaluator.evaluate(d)
            assert decision.route == "direct_response", f"Failed distractor: {d}"
            assert decision.intent == "out_of_domain"

    def test_route_greeting_query(self, evaluator):
        decision = evaluator.evaluate("Hello! What can you do?")
        assert decision.route == "direct_response"
        assert decision.intent == "greeting_or_general"


class TestLangGraphStateTransitions:
    """Tests for StateGraph node registration, conditional edges, and execution trace."""

    def test_evaluate_query_node_attaches_decision_and_trace(self):
        state = AgentState(query="What is the initial response SLA for SEV-1?")
        updated_state = evaluate_query_node(state)

        assert updated_state.route == "static_rag"
        assert updated_state.intent is not None
        assert len(updated_state.execution_trace) == 1
        assert updated_state.execution_trace[0]["node"] == "evaluate_query"
        assert updated_state.execution_trace[0]["duration_ms"] >= 0.0

    def test_route_decision_edge_logic(self):
        s_rag = AgentState(query="test", route="static_rag")
        assert route_decision_edge(s_rag) == "static_rag"

        s_mcp = AgentState(query="test", route="mcp_tools")
        assert route_decision_edge(s_mcp) == "mcp_tools"

        s_hyb = AgentState(query="test", route="hybrid")
        assert route_decision_edge(s_hyb) == "hybrid"

        s_dir = AgentState(query="test", route="direct_response")
        assert route_decision_edge(s_dir) == "direct_response"

    def test_compile_graph_and_execute_direct_greeting(self):
        graph = build_company_intelligence_graph()
        initial_state = AgentState(query="Hello there!")
        final_state = graph.invoke(initial_state)

        assert final_state.route == "direct_response"
        assert "Company Intelligence AI" in final_state.final_answer
        assert len(final_state.execution_trace) >= 2
        nodes_traversed = [step["node"] for step in final_state.execution_trace]
        assert "evaluate_query" in nodes_traversed
        assert "format_response" in nodes_traversed

    def test_compile_graph_and_execute_adversarial_trap(self):
        graph = build_company_intelligence_graph()
        initial_state = AgentState(query="Can I claim a 500,000 INR Rolex watch reimbursement?")
        final_state = graph.invoke(initial_state)

        assert final_state.route == "direct_response"
        assert "not contain sufficient information" in final_state.final_answer


class TestAgentAPIEndpoints:
    """Direct route unit tests for /api/v1/agent/evaluate and /api/v1/agent/query."""

    def test_evaluate_endpoint_authenticated(self):
        orchestrator = AgentOrchestrator()
        payload = AgentQueryRequest(query="Show me active Jira blockers in project ALPHA")

        response = run_coroutine(
            evaluate_query(
                payload=payload,
                _authenticated=settings.INTERNAL_API_KEY,
                orchestrator=orchestrator,
            )
        )

        assert isinstance(response, EvaluateQueryResponse)
        assert response.query == payload.query
        assert response.route == "mcp_tools"
        assert "jira_get_blockers" in response.target_tools

    def test_evaluate_endpoint_hybrid_query(self):
        orchestrator = AgentOrchestrator()
        payload = AgentQueryRequest(query="Is blocker ALPHA-101 violating our SEV-1 response policy?")

        response = run_coroutine(
            evaluate_query(
                payload=payload,
                _authenticated=settings.INTERNAL_API_KEY,
                orchestrator=orchestrator,
            )
        )

        assert response.route == "hybrid"
        assert response.intent == "cross_domain_hybrid"

    def test_query_endpoint_direct_greeting(self):
        orchestrator = AgentOrchestrator()
        payload = AgentQueryRequest(query="Hi, what are your capabilities?")

        response = run_coroutine(
            execute_agent_query(
                payload=payload,
                _authenticated=settings.INTERNAL_API_KEY,
                orchestrator=orchestrator,
            )
        )

        assert isinstance(response, AgentQueryResponse)
        assert response.route == "direct_response"
        assert len(response.answer) > 0
        assert len(response.execution_trace) >= 2
        assert response.latency_ms >= 0.0

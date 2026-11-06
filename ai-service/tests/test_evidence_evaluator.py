"""
Unit and Integration Tests for Day 12: Evidence Evaluator & Citation Validator Node.
Tests citation provenance verification, mathematical grounding scores,
and full LangGraph state machine execution through the evidence evaluator node.
"""

from typing import Any, Dict
import pytest

from app.agent.state import AgentState
from app.agent.validator import CitationValidator, EvidenceEvaluator, evaluate_evidence_node
from app.agent.graph import build_company_intelligence_graph


class TestCitationValidator:
    """Tests provenance extraction and verification across PDFs and MCP applications."""

    def setup_method(self):
        self.validator = CitationValidator()

    def test_validate_pdf_citations_valid(self):
        citations = [{"doc_name": "Company_HR_and_Work_Rules.pdf", "page_number": 1}]
        validated = self.validator.validate_pdf_citations(citations, "")
        assert len(validated) == 1
        assert validated[0]["verified"] is True
        assert validated[0]["source_type"] == "static_pdf"
        assert validated[0]["citation_text"] == "[Company_HR_and_Work_Rules.pdf, Page 1]"

    def test_validate_pdf_citations_invalid_page(self):
        citations = [{"doc_name": "Company_HR_and_Work_Rules.pdf", "page_number": 99}]
        validated = self.validator.validate_pdf_citations(citations, "")
        assert len(validated) == 1
        assert validated[0]["verified"] is False

    def test_validate_pdf_citations_regex_extraction(self):
        text = "Per policy [Engineering_SLA_and_Blocker_Policy.pdf, Page 2], SEV-1 has a 15-minute SLA."
        validated = self.validator.validate_pdf_citations([], text)
        assert len(validated) == 1
        assert validated[0]["verified"] is True
        assert validated[0]["doc_name"] == "Engineering_SLA_and_Blocker_Policy.pdf"
        assert validated[0]["page_number"] == 2

    def test_validate_mcp_citations_jira(self):
        mcp_results = [
            {
                "tool_name": "jira_get_blockers",
                "category": "jira",
                "content": [
                    {
                        "type": "text",
                        "text": '[{"key": "ALPHA-101", "summary": "DB pool exhaustion", "status": "Blocked", "priority": "Highest"}]',
                    }
                ],
            }
        ]
        validated = self.validator.validate_mcp_citations(mcp_results)
        assert len(validated) == 1
        assert validated[0]["source_type"] == "live_mcp"
        assert validated[0]["app"] == "Jira"
        assert validated[0]["identifier"] == "ALPHA-101"
        assert "[Jira: ALPHA-101" in validated[0]["citation_text"]

    def test_validate_mcp_citations_notion(self):
        mcp_results = [
            {
                "tool_name": "notion_get_page",
                "category": "notion",
                "content": [
                    {
                        "type": "text",
                        "text": '{"id": "NOTION-SPEC-01", "title": "Project Alpha Architecture Specification"}',
                    }
                ],
            }
        ]
        validated = self.validator.validate_mcp_citations(mcp_results)
        assert len(validated) == 1
        assert validated[0]["source_type"] == "live_mcp"
        assert validated[0]["app"] == "Notion"
        assert validated[0]["identifier"] == "NOTION-SPEC-01"

    def test_validate_mcp_citations_gmail(self):
        mcp_results = [
            {
                "tool_name": "gmail_get_customer_escalations",
                "category": "gmail",
                "content": [
                    {
                        "type": "text",
                        "text": '[{"thread_id": "THREAD-ACME-01", "subject": "Critical: 504 Gateway Timeouts", "from": "client@acme.com"}]',
                    }
                ],
            }
        ]
        validated = self.validator.validate_mcp_citations(mcp_results)
        assert len(validated) == 1
        assert validated[0]["source_type"] == "live_mcp"
        assert validated[0]["app"] == "Gmail"
        assert validated[0]["identifier"] == "THREAD-ACME-01"


class TestEvidenceEvaluator:
    """Tests mathematical grounding scoring and evidence sufficiency decisions."""

    def setup_method(self):
        self.evaluator = EvidenceEvaluator()

    def test_direct_response_greeting_evaluation(self):
        state = AgentState(
            query="Hello there",
            intent="greeting_or_general",
            route="direct_response",
        )
        score, valid, summary, citations = self.evaluator.evaluate(state)
        assert score == 1.0
        assert valid is True
        assert len(citations) == 0

    def test_direct_response_adversarial_trap_evaluation(self):
        state = AgentState(
            query="How many pet dragons can an employee claim under the wellness policy?",
            intent="adversarial_trap",
            route="direct_response",
        )
        score, valid, summary, citations = self.evaluator.evaluate(state)
        assert score == 1.0
        assert valid is True

    def test_static_rag_evaluation_grounded(self):
        state = AgentState(
            query="What are the core collaboration hours?",
            intent="static_policy_inquiry",
            route="static_rag",
            rag_result={
                "answer": "Core hours are 10:00 to 16:00 IST [Company_HR_and_Work_Rules.pdf, Page 1].",
                "citations": [{"doc_name": "Company_HR_and_Work_Rules.pdf", "page_number": 1}],
                "retrieved_chunks_count": 3,
                "sources_used": ["Company_HR_and_Work_Rules.pdf"],
            },
        )
        score, valid, summary, citations = self.evaluator.evaluate(state)
        assert score >= 0.90
        assert valid is True
        assert len(citations) >= 1
        assert citations[0]["verified"] is True

    def test_static_rag_evaluation_empty_chunks(self):
        state = AgentState(
            query="Unrelated query",
            intent="static_policy_inquiry",
            route="static_rag",
            rag_result={"answer": "", "citations": [], "retrieved_chunks_count": 0},
        )
        score, valid, summary, citations = self.evaluator.evaluate(state)
        assert score < 0.3
        assert valid is False

    def test_mcp_tools_evaluation_grounded(self):
        state = AgentState(
            query="What active blockers exist in sprint?",
            intent="live_ops_inquiry",
            route="mcp_tools",
            mcp_results=[
                {
                    "tool_name": "jira_get_blockers",
                    "category": "jira",
                    "content": [
                        {
                            "type": "text",
                            "text": '[{"key": "ALPHA-101", "status": "Blocked", "priority": "Highest"}]',
                        }
                    ],
                }
            ],
        )
        score, valid, summary, citations = self.evaluator.evaluate(state)
        assert score >= 0.85
        assert valid is True
        assert len(citations) == 1
        assert citations[0]["identifier"] == "ALPHA-101"

    def test_hybrid_evaluation_cross_domain(self):
        state = AgentState(
            query="What is the SLA for blocker ALPHA-101?",
            intent="cross_domain_hybrid",
            route="hybrid",
            rag_result={
                "answer": "SEV-1 response time is 15 minutes [Engineering_SLA_and_Blocker_Policy.pdf, Page 2].",
                "citations": [{"doc_name": "Engineering_SLA_and_Blocker_Policy.pdf", "page_number": 2}],
                "retrieved_chunks_count": 2,
            },
            mcp_results=[
                {
                    "tool_name": "jira_get_issue_details",
                    "category": "jira",
                    "content": [
                        {
                            "type": "text",
                            "text": '{"key": "ALPHA-101", "summary": "Payment pool exhaustion", "status": "Blocked"}',
                        }
                    ],
                }
            ],
        )
        score, valid, summary, citations = self.evaluator.evaluate(state)
        assert score >= 0.95
        assert valid is True
        assert len(citations) == 2
        source_types = {c["source_type"] for c in citations}
        assert "static_pdf" in source_types
        assert "live_mcp" in source_types


class TestLangGraphEvidenceIntegration:
    """Tests end-to-end graph execution ensuring evaluate_evidence node fires and records metrics."""

    def test_full_graph_static_rag_execution(self):
        graph = build_company_intelligence_graph()
        state = AgentState(query="What are the core collaboration hours?")
        final_state = graph.invoke(state)

        # 1. State must have passed through evaluate_evidence node
        nodes_executed = [step["node"] for step in final_state.execution_trace]
        assert "evaluate_query" in nodes_executed
        assert "execute_static_rag" in nodes_executed
        assert "evaluate_evidence" in nodes_executed
        assert "format_response" in nodes_executed

        # 2. Evidence fields must be populated
        assert final_state.grounding_score > 0.0
        assert final_state.evidence_valid is True
        assert len(final_state.structured_citations) > 0
        assert final_state.final_answer is not None
        assert "10:00" in final_state.final_answer or "16:00" in final_state.final_answer

    def test_full_graph_hybrid_execution(self):
        graph = build_company_intelligence_graph()
        state = AgentState(query="What is our SEV-1 SLA and what are the details for blocker ALPHA-101?")
        final_state = graph.invoke(state)

        nodes_executed = [step["node"] for step in final_state.execution_trace]
        assert "evaluate_evidence" in nodes_executed
        assert final_state.route == "hybrid"
        assert final_state.grounding_score >= 0.90
        assert len(final_state.structured_citations) >= 2
        assert any(c["source_type"] == "static_pdf" for c in final_state.structured_citations)
        assert any(c["source_type"] == "live_mcp" for c in final_state.structured_citations)

    def test_full_graph_adversarial_trap_rejection(self):
        graph = build_company_intelligence_graph()
        state = AgentState(query="Can an employee expense a gold Rolex watch on the company card?")
        final_state = graph.invoke(state)

        nodes_executed = [step["node"] for step in final_state.execution_trace]
        assert "evaluate_evidence" in nodes_executed
        assert final_state.route == "direct_response"
        assert "not contain sufficient information" in final_state.final_answer.lower()

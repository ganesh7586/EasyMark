"""
Unit and Integration Tests for Day 13: Conversation Memory & State Checkpointing.
Tests MongoDB checkpoint persistence, multi-turn dialogue management,
pronoun coreference resolution, and stateful agent orchestrator workflows.
"""

from typing import Any, Dict
import mongomock
import pytest
from starlette.testclient import TestClient

from app.agent.orchestrator import AgentOrchestrator
from app.agent.state import AgentState
from app.api.agent import (
    AgentQueryRequest,
    AgentQueryResponse,
    execute_agent_query,
    get_thread_history,
    delete_thread,
)
from app.core.config import settings
from app.core.database import DatabaseManager
from app.memory.manager import MemoryManager


def run_coroutine(coro):
    """Directly drives synchronous coroutines without spinning up socket-bound loops."""
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value


class TestDatabaseCheckpoints:
    """Tests raw MongoDB checkpoint CRUD operations."""

    def setup_method(self):
        self.mock_client = mongomock.MongoClient()
        self.db = DatabaseManager(uri=None, db_name="test_memory_db", client=self.mock_client)
        self.db.init_indexes()

    def test_save_and_retrieve_checkpoint(self):
        cp_id = self.db.save_checkpoint(
            "thread-001",
            {
                "turn_index": 1,
                "query": "Show me Jira blockers",
                "answer": "ALPHA-101 is blocked",
                "extracted_entities": {"jira_issues": ["ALPHA-101"]},
            },
        )
        assert cp_id is not None

        latest = self.db.get_latest_checkpoint("thread-001")
        assert latest is not None
        assert latest["thread_id"] == "thread-001"
        assert latest["turn_index"] == 1
        assert latest["answer"] == "ALPHA-101 is blocked"

    def test_get_thread_history_ordering(self):
        for idx in range(1, 4):
            self.db.save_checkpoint(
                "thread-002",
                {
                    "turn_index": idx,
                    "query": f"Question {idx}",
                    "answer": f"Answer {idx}",
                },
            )

        history = self.db.get_thread_history("thread-002", limit=10)
        assert len(history) == 3
        assert [h["turn_index"] for h in history] == [1, 2, 3]

    def test_delete_thread(self):
        self.db.save_checkpoint("thread-del", {"turn_index": 1, "query": "test"})
        self.db.save_checkpoint("thread-del", {"turn_index": 2, "query": "test2"})

        deleted = self.db.delete_thread("thread-del")
        assert deleted == 2

        history = self.db.get_thread_history("thread-del")
        assert len(history) == 0


class TestMemoryManager:
    """Tests MemoryManager coreference resolution and context accumulation."""

    def setup_method(self):
        self.mock_client = mongomock.MongoClient()
        self.db = DatabaseManager(uri=None, db_name="test_mem_mgr_db", client=self.mock_client)
        self.db.init_indexes()
        self.memory = MemoryManager(db_manager=self.db)

    def test_load_empty_thread_context(self):
        turn_idx, history, entities = self.memory.load_thread_context("non-existent-thread")
        assert turn_idx == 1
        assert history == []
        assert entities == {}

    def test_record_turn_and_reload(self):
        state = AgentState(
            query="Show blockers",
            final_answer="ALPHA-101 is currently blocked.",
            intent="live_ops_inquiry",
            route="mcp_tools",
            turn_index=1,
            extracted_entities={"jira_issues": ["ALPHA-101"], "severities": ["SEV-1"]},
        )

        doc_id = self.memory.record_turn("thread-test", "user_1", state)
        assert doc_id is not None

        turn_idx, history, entities = self.memory.load_thread_context("thread-test")
        assert turn_idx == 2
        assert len(history) == 1
        assert "ALPHA-101" in entities["jira_issues"]
        assert "SEV-1" in entities["severities"]

    def test_coreference_resolution_pronoun(self):
        entities = {"jira_issues": ["ALPHA-101"], "severities": ["SEV-1"]}
        history = [{"turn_index": 1, "query": "Show blockers"}]

        # "Who is assigned to it?" -> resolves to "Who is assigned to blocker ALPHA-101?"
        resolved = self.memory.resolve_coreferences("Who is assigned to it?", entities, history)
        assert "ALPHA-101" in resolved
        assert "it" not in resolved.lower()

    def test_coreference_resolution_sla(self):
        entities = {"jira_issues": ["ALPHA-101"], "severities": ["SEV-1"]}
        history = [{"turn_index": 1, "query": "Show blockers"}]

        # "What is the SLA for it?" -> resolves with issue key and severity
        resolved = self.memory.resolve_coreferences("What is the SLA for it?", entities, history)
        assert "ALPHA-101" in resolved
        assert "SEV-1" in resolved

    def test_unambiguous_query_unchanged(self):
        entities = {"jira_issues": ["ALPHA-101"]}
        history = [{"turn_index": 1, "query": "Show blockers"}]

        orig = "What are the core collaboration hours?"
        resolved = self.memory.resolve_coreferences(orig, entities, history)
        assert resolved == orig


class TestMultiTurnOrchestratorIntegration:
    """Tests stateful multi-turn conversation flow across consecutive turns."""

    def setup_method(self):
        self.mock_client = mongomock.MongoClient()
        self.db = DatabaseManager(uri=None, db_name="test_orchestrator_mem", client=self.mock_client)
        self.db.init_indexes()
        self.memory = MemoryManager(db_manager=self.db)
        self.orchestrator = AgentOrchestrator(memory_manager=self.memory)

    def test_two_turn_blocker_investigation_flow(self):
        thread_id = "investigation-session-999"

        # --- Turn 1: Discover Active Blockers ---
        t1_state = self.orchestrator.process_query(
            query="Show me all active blockers in Jira",
            thread_id=thread_id,
            user_id="engineer_alice",
        )
        assert t1_state.turn_index == 1
        assert t1_state.route == "mcp_tools"
        assert "ALPHA-101" in t1_state.final_answer or "ALPHA-104" in t1_state.final_answer

        # --- Turn 2: Follow-up with Pronoun Reference ("Who is assigned to it?") ---
        t2_state = self.orchestrator.process_query(
            query="Who is assigned to it?",
            thread_id=thread_id,
            user_id="engineer_alice",
        )
        assert t2_state.turn_index == 2
        # Coreference must have resolved "it" to ALPHA-101 or ALPHA-104
        assert t2_state.resolved_query is not None
        assert "ALPHA-10" in t2_state.resolved_query
        assert t2_state.route == "mcp_tools"
        # Sarah Chen is the senior backend engineer assigned to ALPHA-101
        assert "Sarah Chen" in t2_state.final_answer or "assignee" in t2_state.final_answer.lower()

        # Verify history in database
        history = self.orchestrator.get_thread_history(thread_id)
        assert len(history) == 2
        assert history[0]["turn_index"] == 1
        assert history[1]["turn_index"] == 2

        # Clear session
        deleted = self.orchestrator.clear_thread(thread_id)
        assert deleted == 2
        assert len(self.orchestrator.get_thread_history(thread_id)) == 0


class TestFastAPIThreadEndpoints:
    """Tests REST API endpoints for thread history and session reset."""

    def setup_method(self):
        self.mock_client = mongomock.MongoClient()
        self.db = DatabaseManager(uri=None, db_name="test_api_thread_mem", client=self.mock_client)
        self.db.init_indexes()
        self.memory = MemoryManager(db_manager=self.db)
        self.orchestrator = AgentOrchestrator(memory_manager=self.memory)
        self.auth_key = settings.INTERNAL_API_KEY

    def test_thread_history_and_delete_endpoints(self):
        # 1. Post a query with a thread_id
        payload = AgentQueryRequest(query="Hello", thread_id="api-thread-test")
        post_resp = run_coroutine(
            execute_agent_query(
                payload=payload,
                _authenticated=self.auth_key,
                orchestrator=self.orchestrator,
            )
        )
        assert post_resp.thread_id == "api-thread-test"
        assert post_resp.turn_index == 1

        # 2. Query thread history endpoint
        hist_resp = run_coroutine(
            get_thread_history(
                thread_id="api-thread-test",
                limit=10,
                _authenticated=self.auth_key,
                orchestrator=self.orchestrator,
            )
        )
        assert hist_resp.thread_id == "api-thread-test"
        assert hist_resp.total_turns == 1
        assert len(hist_resp.history) == 1

        # 3. Delete thread endpoint
        del_resp = run_coroutine(
            delete_thread(
                thread_id="api-thread-test",
                _authenticated=self.auth_key,
                orchestrator=self.orchestrator,
            )
        )
        assert del_resp.status == "cleared"
        assert del_resp.deleted_turns == 1

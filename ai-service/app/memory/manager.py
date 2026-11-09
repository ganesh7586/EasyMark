"""
Conversation Memory & State Checkpointing Manager.
Day 13: Stateful multi-turn dialogue management, MongoDB checkpoint persistence,
and contextual coreference query resolution.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple

from app.agent.state import AgentState
from app.core.database import DatabaseManager, get_db


@dataclass
class ConversationTurn:
    """Represents a single conversational turn in a thread session."""

    turn_index: int
    query: str
    resolved_query: Optional[str]
    answer: str
    intent: str
    route: str
    grounding_score: float
    citations: List[Dict[str, Any]]
    structured_citations: List[Dict[str, Any]]
    sources_used: List[str]
    extracted_entities: Dict[str, Any]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MemoryManager:
    """
    Manages conversation sessions, state checkpoint persistence, and multi-turn context.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or get_db()

    def load_thread_context(self, thread_id: Optional[str]) -> Tuple[int, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Loads prior turns and accumulated entity context for a given thread_id.

        Args:
            thread_id: Unique session identifier or None for stateless queries.

        Returns:
            Tuple of:
            - next_turn_index (int)
            - conversation_history (List of past turn summaries)
            - accumulated_entities (Merged entity dictionary from past turns)
        """
        if not thread_id:
            return (1, [], {})

        past_checkpoints = self.db.get_thread_history(thread_id, limit=20)
        if not past_checkpoints:
            return (1, [], {})

        next_turn_index = len(past_checkpoints) + 1

        history: List[Dict[str, Any]] = []
        accumulated_entities: Dict[str, Any] = {
            "jira_issues": [],
            "severities": [],
            "notion_ids": [],
            "likely_doc": None,
        }

        for cp in past_checkpoints:
            history.append({
                "turn_index": cp.get("turn_index", 1),
                "query": cp.get("query", ""),
                "resolved_query": cp.get("resolved_query"),
                "answer": cp.get("answer", ""),
                "intent": cp.get("intent", ""),
                "route": cp.get("route", ""),
                "grounding_score": cp.get("grounding_score", 0.0),
                "citations": cp.get("citations", []),
                "structured_citations": cp.get("structured_citations", []),
                "sources_used": cp.get("sources_used", []),
                "created_at": cp.get("created_at", ""),
            })

            # Merge entities chronologically (later turns append/override)
            ents = cp.get("extracted_entities", {})
            for key in ["jira_issues", "severities", "notion_ids"]:
                for val in ents.get(key, []):
                    if val not in accumulated_entities[key]:
                        accumulated_entities[key].append(val)

            if ents.get("likely_doc"):
                accumulated_entities["likely_doc"] = ents["likely_doc"]

        return (next_turn_index, history, accumulated_entities)

    def resolve_coreferences(
        self,
        query: str,
        accumulated_entities: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> str:
        """
        Detects pronouns and anaphoric follow-up references in the user query
        and resolves them using accumulated context from previous turns.

        Examples:
            Turn 1: "Show me blockers in Jira." (produces ALPHA-101)
            Turn 2: "Who is assigned to it?" -> "Who is assigned to blocker ALPHA-101?"
            Turn 2: "What is its SLA?" -> "What is the SLA for SEV-1 blocker ALPHA-101?"
        """
        if not accumulated_entities or not history:
            return query

        clean_q = query.strip()
        q_lower = clean_q.lower()

        # Target entities from previous context
        past_issues = accumulated_entities.get("jira_issues", [])
        past_sevs = accumulated_entities.get("severities", [])
        past_notion = accumulated_entities.get("notion_ids", [])
        past_doc = accumulated_entities.get("likely_doc")

        active_issue = past_issues[-1] if past_issues else None
        active_sev = past_sevs[-1] if past_sevs else None
        active_notion = past_notion[-1] if past_notion else None

        # 1. Resolve Jira issue pronoun references ("it", "that blocker", "the ticket")
        issue_pronoun_patterns = [
            r"\b(who is assigned to (?:it|that|the ticket|the blocker|this))\b",
            r"\b(what is the status of (?:it|that|the ticket|the blocker|this))\b",
            r"\b(details for (?:it|that|the blocker|the ticket))\b",
            r"\b(about (?:it|that ticket|that blocker))\b",
            r"\b(assigned to (?:it|that))\b",
            r"\b(status of (?:it|that))\b",
        ]

        if active_issue:
            def _replace_pronoun(match):
                word = match.group(0).lower()
                if word == "its":
                    return f"{active_issue}'s"
                return f"blocker {active_issue}"

            pronoun_target_pattern = r"\b(?:it|its|that|this|the ticket|the blocker|that ticket|that blocker)\b"

            # Direct pattern matches
            has_pattern_match = any(re.search(pat, q_lower) for pat in issue_pronoun_patterns)
            if has_pattern_match or re.search(r"\b(?:it|its|that blocker|the blocker|that ticket)\b", q_lower):
                if not any(iss in clean_q for iss in past_issues):
                    clean_q = re.sub(
                        pronoun_target_pattern,
                        _replace_pronoun,
                        clean_q,
                        flags=re.IGNORECASE,
                    )

        # 2. Resolve SLA policy references with active issue/severity
        if active_issue and ("sla" in q_lower or "service level" in q_lower or "response target" in q_lower):
            if active_issue not in clean_q:
                clean_q = f"{clean_q} for blocker {active_issue}"
            if active_sev and active_sev not in clean_q.upper():
                clean_q = f"{clean_q} ({active_sev})"

        # 3. Resolve Notion spec references ("that spec", "the prd", "the page")
        if active_notion and re.search(r"\b(that spec|the spec|the page|the architecture doc|the prd)\b", q_lower):
            clean_q = re.sub(
                r"\b(?:that spec|the spec|the page|the architecture doc|the prd)\b",
                f"specification {active_notion}",
                clean_q,
                count=1,
                flags=re.IGNORECASE,
            )

        # 4. Resolve document follow-ups ("under that policy", "per that rule")
        if past_doc and re.search(r"\b(that policy|that rule|the handbook|the charter)\b", q_lower):
            if past_doc not in clean_q:
                clean_q = re.sub(
                    r"\b(?:that policy|that rule|the handbook|the charter)\b",
                    f"policy {past_doc}",
                    clean_q,
                    count=1,
                    flags=re.IGNORECASE,
                )

        return clean_q

    def record_turn(self, thread_id: Optional[str], user_id: str, state: AgentState) -> Optional[str]:
        """
        Saves the completed agent execution state as a conversation checkpoint in MongoDB.

        Args:
            thread_id: Session identifier. If None, turn is not persisted.
            user_id: Employee identifier.
            state: Completed AgentState containing query, answer, citations, and trace.

        Returns:
            The MongoDB inserted document ID as a string, or None.
        """
        if not thread_id:
            return None

        # Enrich extracted_entities with entities discovered in verified citations and live tools
        saved_entities = dict(state.extracted_entities)
        for sc in state.structured_citations:
            if sc.get("source_type") == "live_mcp" and sc.get("app") == "Jira":
                ident = sc.get("identifier")
                if ident:
                    saved_entities.setdefault("jira_issues", [])
                    if ident not in saved_entities["jira_issues"]:
                        saved_entities["jira_issues"].append(ident)
            elif sc.get("source_type") == "live_mcp" and sc.get("app") == "Notion":
                ident = sc.get("identifier")
                if ident:
                    saved_entities.setdefault("notion_ids", [])
                    if ident not in saved_entities["notion_ids"]:
                        saved_entities["notion_ids"].append(ident)

        checkpoint_data = {
            "thread_id": thread_id,
            "user_id": user_id or "employee_default",
            "turn_index": state.turn_index,
            "query": state.query,
            "resolved_query": state.resolved_query,
            "answer": state.final_answer or "",
            "intent": state.intent or "unknown",
            "route": state.route or "unknown",
            "confidence": state.confidence,
            "grounding_score": state.grounding_score,
            "evidence_valid": state.evidence_valid,
            "citations": state.citations,
            "structured_citations": state.structured_citations,
            "sources_used": state.sources_used,
            "extracted_entities": saved_entities,
            "latency_ms": state.latency_ms,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        return self.db.save_checkpoint(thread_id, checkpoint_data)

    def get_thread_history(self, thread_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves all conversation checkpoints for a session.
        """
        return self.db.get_thread_history(thread_id, limit=limit)

    def delete_thread(self, thread_id: str) -> int:
        """
        Deletes all checkpoints and history associated with a thread session.
        """
        return self.db.delete_thread(thread_id)


_memory_manager_instance: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Singleton accessor for MemoryManager."""
    global _memory_manager_instance
    if _memory_manager_instance is None:
        _memory_manager_instance = MemoryManager()
    return _memory_manager_instance

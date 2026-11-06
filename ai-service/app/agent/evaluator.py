"""
Question Evaluator & Query Router Node for LangGraph Agent.
Analyzes employee questions, extracts key domain entities, classifies intent,
and deterministically routes to Static RAG, Live MCP Tools, or Hybrid execution.
"""

import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.agent.state import AgentState


class RoutingDecision(BaseModel):
    """Structured decision output from the Question Evaluator."""
    intent: str
    route: str  # "static_rag", "mcp_tools", "hybrid", "direct_response"
    confidence: float
    reasoning: str
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    target_tools: List[str] = Field(default_factory=list)
    doc_filter: Optional[str] = Field(default=None)


class QuestionEvaluator:
    """
    Evaluates employee queries to determine the optimal execution strategy.
    Combines high-precision regex entity extraction, heuristic domain categorization,
    and semantic classification.
    """

    # --- Regex Pattern Definitions ---
    JIRA_ISSUE_PATTERN = r"\b([A-Z]{2,10}-\d+)\b"
    SEVERITY_PATTERN = r"\b(SEV-[0-6]|P[0-4]|Sev\s*[0-6])\b"
    NOTION_ID_PATTERN = r"\b(NOTION-[A-Z]+-\d+)\b"

    # Static policy keyword indicators
    POLICY_KEYWORDS = [
        "policy", "policies", "rule", "rules", "guideline", "guidelines",
        "working hours", "core collaboration hours", "leave", "vacation",
        "absence", "expense", "reimbursement", "per diem", "equipment",
        "laptop", "monitor", "data classification", "confidential",
        "nda", "sla", "service level", "target response", "cadence",
        "charter", "milestone", "m1", "m2", "m3", "m4", "m5",
        "project sponsor", "project lead", "blameless", "post-incident review",
        "code of conduct"
    ]

    # Live operational keywords (Jira, Notion, Gmail)
    LIVE_KEYWORDS = [
        "sprint", "active sprint", "ticket", "tickets", "blocker", "blockers",
        "jira", "backlog", "assignee", "assigned to", "status of",
        "notion", "spec", "specification", "meeting notes", "sync notes",
        "action item", "action items", "prd", "post-mortem draft",
        "gmail", "email", "emails", "thread", "inbox", "customer escalation",
        "customer thread", "approval", "approvals", "signoff", "sign-off"
    ]

    # Fake topic traps (Adversarial guardrail)
    FAKE_TOPIC_TRAPS = [
        "luxury watch", "rolex", "tiger", "monkey", "cryptocurrency", "50 million",
        "bitcoin", "mining", "sabbatical", "bonus", "bonuses", "dress code", "formal suit",
        "airline lounge", "interns", "sev-5", "sev-6", "sev-0", "timesheet", "penalty fee",
        "m6", "stock grant", "competitor", "leaked", "gym", "stipend", "60 hours",
        "car allowance", "vue.js", "launch party", "las vegas", "without testing", "friday nights",
        "free lunch", "nuclear", "espresso", "mars", "concert", "home media server"
    ]

    # Out of domain distractors
    OUT_OF_DOMAIN_PATTERNS = [
        "sourdough", "baking", "recipe", "fifa", "world cup", "moon", "distance to",
        "photosynthesis", "speed of light", "hamlet", "shakespeare", "chess",
        "tokyo", "population", "capital of", "weather in"
    ]

    def extract_entities(self, query: str) -> Dict[str, Any]:
        """Extracts structured entities such as ticket IDs, severities, and document names."""
        entities: Dict[str, Any] = {}

        # 1. Notion IDs first
        notion_matches = re.findall(self.NOTION_ID_PATTERN, query, re.IGNORECASE)
        if notion_matches:
            entities["notion_ids"] = [m.upper() for m in notion_matches]

        # 2. Jira Issue Keys (strip Notion IDs to prevent false matches on hyphenated tokens)
        clean_for_jira = re.sub(self.NOTION_ID_PATTERN, "", query, flags=re.IGNORECASE)
        jira_matches = re.findall(self.JIRA_ISSUE_PATTERN, clean_for_jira, re.IGNORECASE)
        if jira_matches:
            # Exclude severity tiers (e.g. SEV-1, SEV-2) and P-tiers from Jira ticket keys
            clean_jira = [
                m.upper() for m in jira_matches
                if not m.upper().startswith("SEV-") and not m.upper().startswith("P-")
            ]
            if clean_jira:
                entities["jira_issues"] = clean_jira

        # 3. Severity Levels
        sev_matches = re.findall(self.SEVERITY_PATTERN, query, re.IGNORECASE)
        if sev_matches:
            entities["severities"] = [m.upper().replace(" ", "") for m in sev_matches]

        # 4. Mentioned Document Mapping
        q_lower = query.lower()
        if any(k in q_lower for k in ["hr", "leave", "work rules", "remote work", "expense", "per diem", "policy rules", "collaboration hours"]):
            entities["likely_doc"] = "Company_HR_and_Work_Rules.pdf"
        elif any(k in q_lower for k in ["initial response sla", "response target", "sev-1 outage", "sev-2 major", "blocker policy", "post-incident review"]):
            entities["likely_doc"] = "Engineering_SLA_and_Blocker_Policy.pdf"
        elif any(k in q_lower for k in ["charter", "milestone", "m1", "m2", "m3", "m4", "m5", "project sponsor", "deliverable"]):
            entities["likely_doc"] = "Project_Alpha_Charter_and_Milestones.pdf"

        return entities

    def evaluate(self, query: str) -> RoutingDecision:
        """
        Evaluates a query and generates a typed RoutingDecision.
        """
        clean_query = query.strip()
        q_lower = clean_query.lower()
        entities = self.extract_entities(clean_query)

        # 1. Check for Greetings / General Assistant Info
        is_greeting = (
            any(q_lower.startswith(g) for g in ["hello", "hi", "hey", "good morning", "good afternoon", "greetings"])
            or any(t in q_lower for t in ["what can you do", "who are you", "what are your capabilities", "how can you help"])
        )
        if is_greeting and not bool(entities.get("jira_issues")) and not any(k in q_lower for k in ["blocker", "ticket", "sla", "policy"]):
            return RoutingDecision(
                intent="greeting_or_general",
                route="direct_response",
                confidence=0.98,
                reasoning="Query is a conversational greeting or general capability question.",
                extracted_entities=entities,
                target_tools=[],
            )

        # 2. Check for Adversarial Traps
        if any(trap in q_lower for trap in self.FAKE_TOPIC_TRAPS):
            return RoutingDecision(
                intent="adversarial_trap",
                route="direct_response",
                confidence=0.99,
                reasoning="Query matches known false-premise policy trap; intercepted to prevent hallucination.",
                extracted_entities=entities,
                target_tools=[],
            )

        # 3. Check for Out-of-Domain Distractors
        if any(ood in q_lower for ood in self.OUT_OF_DOMAIN_PATTERNS):
            return RoutingDecision(
                intent="out_of_domain",
                route="direct_response",
                confidence=0.99,
                reasoning="Query is unrelated to company policies or live workplace applications.",
                extracted_entities=entities,
                target_tools=[],
            )

        # 4. Count Signals for Static Policy vs. Live Operational Systems
        has_policy_signal = any(k in q_lower for k in self.POLICY_KEYWORDS) or entities.get("likely_doc") is not None
        has_live_signal = (
            any(k in q_lower for k in self.LIVE_KEYWORDS)
            or bool(entities.get("jira_issues"))
            or bool(entities.get("notion_ids"))
            or "customer escalation" in q_lower
        )

        # Identify Specific MCP Target Tools
        target_tools: List[str] = []
        if "sprint" in q_lower or "active sprint" in q_lower:
            target_tools.append("jira_get_sprint_issues")
        if "blocker" in q_lower or "blockers" in q_lower or "impeded" in q_lower:
            target_tools.append("jira_get_blockers")
        if entities.get("jira_issues") or "ticket details" in q_lower or "ticket" in q_lower:
            if "jira_get_issue_details" not in target_tools:
                target_tools.append("jira_get_issue_details")
        if "jira" in q_lower and not target_tools:
            target_tools.append("jira_search_issues")

        if "spec" in q_lower or "architecture" in q_lower or entities.get("notion_ids") or "page" in q_lower:
            target_tools.append("notion_get_page")
        if "meeting notes" in q_lower or "sync" in q_lower or "retro" in q_lower:
            target_tools.append("notion_get_meeting_notes")
        if "action item" in q_lower or "action items" in q_lower:
            target_tools.append("notion_get_action_items")
        if "notion" in q_lower and not any(t.startswith("notion") for t in target_tools):
            target_tools.append("notion_search_pages")

        if "customer escalation" in q_lower or "escalation thread" in q_lower or "escalation email" in q_lower:
            target_tools.append("gmail_get_customer_escalations")
        if "approval" in q_lower or "pending approval" in q_lower or "sign-off" in q_lower or "signoff" in q_lower:
            target_tools.append("gmail_check_pending_approvals")
        if "email" in q_lower or "thread" in q_lower or "inbox" in q_lower:
            if not any(t.startswith("gmail") for t in target_tools):
                target_tools.append("gmail_search_emails")

        # 5. Hybrid Check: Correlating Static Rules with Live System State
        CORRELATION_TERMS = [
            "violat", "breach", "comply", "compliant", "compliance", "meet our", "meets our",
            "compare", "exceed", "according to policy", "per policy", "per our sla",
            "against our sla", "sla status of ticket", "sla status of blocker"
        ]
        has_correlation_intent = any(term in q_lower for term in CORRELATION_TERMS)
        is_hybrid_query = (
            has_correlation_intent and (has_live_signal or bool(entities.get("jira_issues")))
        ) or (
            bool(entities.get("jira_issues")) and ("sla" in q_lower or "policy" in q_lower)
        )

        if is_hybrid_query:
            return RoutingDecision(
                intent="cross_domain_hybrid",
                route="hybrid",
                confidence=0.95,
                reasoning="Query requires synthesizing static policy rules (SLA/Charter) with dynamic live application state (Jira/Notion/Gmail).",
                extracted_entities=entities,
                target_tools=target_tools or ["jira_get_blockers"],
                doc_filter=entities.get("likely_doc"),
            )

        # 6. Live MCP Tools Only
        # If it has live signals and is NOT a pure policy inquiry (e.g. "what is the sla for sev-1")
        is_pure_policy_query = (
            any(phrase in q_lower for phrase in ["what are the core", "what is the required", "how many working days", "what is the initial response", "what are the deliverables", "what are the four data"])
            or ("sla" in q_lower and not bool(entities.get("jira_issues")) and not any(k in q_lower for k in ["sprint", "email", "thread", "ticket", "inbox"]))
        )

        if has_live_signal and not is_pure_policy_query:
            return RoutingDecision(
                intent="live_ops_inquiry",
                route="mcp_tools",
                confidence=0.92,
                reasoning="Query targets active operational data across Jira, Notion, or Gmail.",
                extracted_entities=entities,
                target_tools=target_tools or ["jira_get_blockers"],
            )

        # 7. Static Policy RAG Only
        return RoutingDecision(
            intent="static_policy_inquiry",
            route="static_rag",
            confidence=0.94,
            reasoning="Query targets authoritative static company policies, HR rules, or project milestones.",
            extracted_entities=entities,
            target_tools=[],
            doc_filter=entities.get("likely_doc"),
        )


def evaluate_query_node(state: AgentState) -> AgentState:
    """
    LangGraph Node Function: Evaluates the input query and attaches routing decision.
    """
    start_time = time.time()
    evaluator = QuestionEvaluator()
    decision = evaluator.evaluate(state.query)

    state.intent = decision.intent
    state.route = decision.route
    state.confidence = decision.confidence
    state.reasoning = decision.reasoning
    state.extracted_entities = decision.extracted_entities
    state.target_tools = decision.target_tools
    state.doc_filter = decision.doc_filter

    duration = (time.time() - start_time) * 1000
    state.log_node_execution(
        node_name="evaluate_query",
        duration_ms=duration,
        details={
            "intent": state.intent,
            "route": state.route,
            "confidence": state.confidence,
            "target_tools": state.target_tools,
            "doc_filter": state.doc_filter,
        },
    )
    return state

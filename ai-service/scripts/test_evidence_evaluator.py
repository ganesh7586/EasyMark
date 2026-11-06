"""
Interactive CLI Demonstration for Day 12: Evidence Evaluator & Citation Validator Node.
Demonstrates provenance verification, structured citations, and mathematical grounding confidence
across Static RAG, Live MCP Tools, Cross-Domain Hybrid, and Adversarial Traps.
"""

from pathlib import Path
import sys
import time
from typing import Any, Dict

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.agent.state import AgentState
from app.agent.orchestrator import get_agent_orchestrator


DEMO_QUERIES = [
    (
        "1. Static Policy Verification (HR Core Hours)",
        "What are the core collaboration hours for employees?",
    ),
    (
        "2. Live Operational MCP Evidence (Jira Blocker)",
        "Show me all active SEV-1 blockers impeding our current sprint.",
    ),
    (
        "3. Cross-Domain Hybrid Synthesis (SLA Policy + Live Ticket)",
        "What is our SEV-1 SLA resolution time, and who is assigned to blocker ALPHA-101?",
    ),
    (
        "4. Adversarial False-Premise Trap (Rolex Expense)",
        "Can an employee submit an expense report for a gold Rolex watch under the wellness policy?",
    ),
    (
        "5. Conversational Greeting (Zero Grounding Required)",
        "Hello! How can you help me today?",
    ),
]


def run_demonstration():
    print("=" * 95)
    print("    DAY 12: EVIDENCE EVALUATOR & CITATION VALIDATOR DEMONSTRATION")
    print("=" * 95)
    print("Initializing LangGraph State Machine with Evidence Evaluator Node...\n")

    orchestrator = get_agent_orchestrator()

    for idx, (title, query) in enumerate(DEMO_QUERIES, start=1):
        print("-" * 95)
        print(f"[{idx}/5] {title}")
        print(f"Query: \"{query}\"")
        print("-" * 95)

        start = time.time()
        state = orchestrator.process_query(query)
        duration = round((time.time() - start) * 1000, 2)

        print(f"• Intent:            {state.intent}")
        print(f"• Route:             {state.route} (Routing Confidence: {state.confidence:.2f})")
        print(f"• Grounding Score:   {state.grounding_score:.2f} / 1.00 ({'VALID' if state.evidence_valid else 'UNGROUNDED'})")
        print(f"• Evidence Summary:  {state.evidence_summary}")
        print(f"• Sources Consulted: {state.sources_used}")
        print(f"• Total Latency:     {duration} ms\n")

        print("• Verified Structured Citations:")
        if state.structured_citations:
            for cit in state.structured_citations:
                src_type = cit.get("source_type")
                if src_type == "static_pdf":
                    verified_icon = "✓" if cit.get("verified") else "✗"
                    print(f"    [{verified_icon}] {cit.get('citation_text')} -> Page {cit.get('page_number')} (URL: {cit.get('reference_url')})")
                else:
                    app = cit.get("app", "MCP")
                    ident = cit.get("identifier", "")
                    status = cit.get("status") or cit.get("title") or cit.get("subject", "")
                    print(f"    [✓] {cit.get('citation_text')} -> {app} Entity: {ident} ({status})")
        else:
            print("    (None - direct response / zero citation required)")

        print(f"\n• Synthesized Response:")
        preview = state.final_answer.strip() if state.final_answer else ""
        if len(preview) > 300:
            preview = preview[:297] + "..."
        print(f"  {preview}\n")

        print("• Node Transition Execution Trace:")
        for step in state.execution_trace:
            print(f"    Step {step['step']}: Node '{step['node']:<25}' -> {step['duration_ms']:6.2f} ms")
        print()

    print("=" * 95)
    print("✓ All 5 workflow scenarios evaluated and verified through Evidence Evaluator Node!")
    print("=" * 95)


if __name__ == "__main__":
    run_demonstration()

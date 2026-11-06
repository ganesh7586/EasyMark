"""
Interactive CLI Verification Script for Day 11.
Demonstrates LangGraph Question Evaluator, Query Router Node, and State Graph Orchestration.
"""

import sys
import time
from pathlib import Path

# Add ai-service to path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.agent.evaluator import QuestionEvaluator
from app.agent.orchestrator import AgentOrchestrator


def main():
    print("=" * 80)
    print("  COMPANY INTELLIGENCE AI - LANGGRAPH QUESTION EVALUATOR & ROUTER (DAY 11)")
    print("=" * 80)

    evaluator = QuestionEvaluator()
    orchestrator = AgentOrchestrator()

    sample_queries = [
        # 1. Static Policy RAG
        (
            "Static Policy RAG",
            "What are the core collaboration hours and what advance notice is required for planned leave?",
        ),
        # 2. Live MCP Jira Tools
        (
            "Live MCP Jira Tools",
            "What are the active blocker tickets currently impeding work in the active sprint?",
        ),
        # 3. Live MCP Notion Tools
        (
            "Live MCP Notion Tools",
            "Retrieve page NOTION-SPEC-01 for technical architecture and milestone M2 specifications.",
        ),
        # 4. Live MCP Gmail Tools
        (
            "Live MCP Gmail Tools",
            "Show all SEV-1 customer escalation email threads from Acme Corp.",
        ),
        # 5. Cross-Domain Hybrid Correlation
        (
            "Cross-Domain Hybrid",
            "Is the open blocker ticket ALPHA-101 violating our official SEV-1 SLA response policy?",
        ),
        # 6. Adversarial Trap Interception
        (
            "Adversarial Policy Trap",
            "Can I get reimbursed for a 500,000 INR Rolex watch under company policy?",
        ),
        # 7. Conversational Greeting
        (
            "Direct Greeting",
            "Hello! What are your capabilities?",
        ),
    ]

    print("\n[Phase 1] Demonstrating Intent Classification & Deterministic Routing\n" + "-" * 80)
    for category, query in sample_queries:
        decision = evaluator.evaluate(query)
        print(f"[{category}]")
        print(f"  Q:          \"{query}\"")
        print(f"  Route:      --> {decision.route.upper()} (Intent: {decision.intent})")
        print(f"  Confidence: {decision.confidence * 100:.1f}%")
        print(f"  Reasoning:  {decision.reasoning}")
        if decision.target_tools:
            print(f"  MCP Tools:  {decision.target_tools}")
        if decision.extracted_entities:
            print(f"  Entities:   {decision.extracted_entities}")
        print("-" * 80)

    print("\n[Phase 2] Executing Full LangGraph State Machine Workflow\n" + "-" * 80)
    demo_query = "Is the open blocker ticket ALPHA-101 violating our official SEV-1 SLA response policy?"
    print(f"Executing Query: \"{demo_query}\"")
    print("Driving LangGraph through START -> evaluate_query -> [hybrid] -> format_response -> END...\n")

    start_exec = time.time()
    final_state = orchestrator.process_query(demo_query, thread_id="demo-session-day11")
    duration = (time.time() - start_exec) * 1000

    print("Execution Completed Successfully!")
    print(f"  Route Taken:    {final_state.route}")
    print(f"  Intent:         {final_state.intent}")
    print(f"  Sources Used:   {final_state.sources_used}")
    print(f"  Total Latency:  {final_state.latency_ms:.2f} ms\n")

    print("Chronological Graph Execution Trace:")
    for step in final_state.execution_trace:
        print(f"  Step {step['step']}: Node '{step['node']:<28}' completed in {step['duration_ms']:6.2f} ms")
        if step.get("details"):
            print(f"          Details: {step['details']}")

    print("\nSynthesized Answer Preview:")
    print("=" * 80)
    print(final_state.final_answer[:500] + ("..." if len(final_state.final_answer) > 500 else ""))
    print("=" * 80)
    print("\n[+] Day 11 LangGraph Question Evaluator & Query Router fully operational!\n")


if __name__ == "__main__":
    main()

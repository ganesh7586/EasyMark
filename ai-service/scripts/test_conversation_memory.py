"""
Interactive CLI Demonstration for Day 13: Conversation Memory & State Checkpointing.
Demonstrates stateful multi-turn dialogue, pronoun coreference resolution across turns,
and MongoDB checkpoint inspection.
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

from app.agent.orchestrator import get_agent_orchestrator


SESSION_THREAD_ID = f"demo-session-{int(time.time())}"

DIALOGUE_TURNS = [
    (
        "Turn 1: Blocker Discovery",
        "Show me all active blockers in Jira impeding Milestone M2.",
    ),
    (
        "Turn 2: Follow-up with Pronoun Reference",
        "Who is assigned to it and what is its status?",
    ),
    (
        "Turn 3: Policy Cross-Correlation on Context Entity",
        "What is the SLA response target for it?",
    ),
]


def run_demonstration():
    print("=" * 95)
    print("    DAY 13: CONVERSATION MEMORY & STATE CHECKPOINTING DEMONSTRATION")
    print("=" * 95)
    print(f"Session Thread ID: {SESSION_THREAD_ID}\n")

    orchestrator = get_agent_orchestrator()

    for idx, (title, query) in enumerate(DIALOGUE_TURNS, start=1):
        print("-" * 95)
        print(f"[{idx}/3] {title}")
        print(f"User Query:     \"{query}\"")
        print("-" * 95)

        start = time.time()
        state = orchestrator.process_query(
            query=query,
            thread_id=SESSION_THREAD_ID,
            user_id="lead_architect",
        )
        duration = round((time.time() - start) * 1000, 2)

        if state.resolved_query:
            print(f"★ Context Resolved Query: \"{state.resolved_query}\"")
        else:
            print(f"• Resolved Query:         (Unmodified)")

        print(f"• Turn Index:             {state.turn_index}")
        print(f"• Classified Intent:      {state.intent}")
        print(f"• Graph Route:            {state.route} (Confidence: {state.confidence:.2f})")
        print(f"• Grounding Score:        {state.grounding_score:.2f} / 1.00 ({'VALID' if state.evidence_valid else 'UNGROUNDED'})")
        print(f"• Accumulated Entities:   {state.accumulated_entities}")
        print(f"• Target Tools Run:       {state.target_tools}")
        print(f"• Turn Latency:           {duration} ms\n")

        print("• Synthesized Response:")
        preview = state.final_answer.strip() if state.final_answer else ""
        if len(preview) > 280:
            preview = preview[:277] + "..."
        print(f"  {preview}\n")

        if state.structured_citations:
            print("• Verified Citations:")
            for cit in state.structured_citations:
                print(f"    [✓] {cit.get('citation_text')}")
        print()

    # Inspect Checkpoint History stored in MongoDB
    print("=" * 95)
    print("               MONGODB CONVERSATION CHECKPOINT AUDIT")
    print("=" * 95)
    history = orchestrator.get_thread_history(SESSION_THREAD_ID)
    print(f"Total Checkpoints Persisted in Database: {len(history)}\n")
    for cp in history:
        print(
            f"  [Turn {cp['turn_index']}] Query: \"{cp['query'][:35]}...\" | "
            f"Route: {cp['route']:<12} | Score: {cp['grounding_score']:.2f} | Time: {cp['created_at']}"
        )
    print()

    # Clear Session
    deleted = orchestrator.clear_thread(SESSION_THREAD_ID)
    print(f"✓ Cleaned up {deleted} session checkpoints from MongoDB for '{SESSION_THREAD_ID}'.")
    print("=" * 95)


if __name__ == "__main__":
    run_demonstration()

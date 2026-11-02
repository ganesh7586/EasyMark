"""
Script: query_policy.py
Purpose: Interactive CLI to query static company policy documents with Groq LLM RAG.
Day 5 demonstration script.
"""

from pathlib import Path
import sys
import time

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.rag.rag_service import get_rag_service


def main():
    default_query = "What is the initial response SLA for a SEV-1 production outage, and who is notified?"
    query = sys.argv[1] if len(sys.argv) > 1 else default_query

    print("=" * 70)
    print("[DAY 5] STATIC COMPANY RULES RAG QUERY DEMONSTRATION")
    print("=" * 70)
    print(f"\n[Question] \"{query}\"\n")

    rag = get_rag_service()

    # If running in sandboxed or offline mode with an unpopulated in-memory fallback,
    # auto-index the local company-docs so retrieval works out-of-the-box.
    if rag.db.get_total_chunks() == 0:
        docs_dir = BASE_DIR.parent / "company-docs"
        if docs_dir.exists():
            print("[Notice] Local store empty (offline/mock mode). Indexing company-docs into memory...")
            from app.ingestion.indexer import StaticDocIndexer
            indexer = StaticDocIndexer(db_manager=rag.db)
            indexer.ingest_all_documents(docs_dir)

    start_time = time.time()
    result = rag.query(query, top_k=3)
    duration = time.time() - start_time

    print("-" * 70)
    print("[AI Answer grounded in Company Policy]")
    print("-" * 70)
    print(result.answer)
    print("\n" + "-" * 70)
    print(f"[Citations Attached] ({len(result.citations)} found):")
    for cit in result.citations:
        print(f"  * Document: {cit['doc_name']} | Page: {cit['page_number']}")

    print(f"\n[Sources Consulted]: {', '.join(result.sources_used)}")
    print(f"[Retrieved Chunks]: {result.retrieved_chunks_count} chunks")
    print(f"[Latency]: {result.latency_ms} ms (Total wall clock: {duration:.2f}s)")
    print(f"[Model]: {result.model}")
    print("=" * 70)


if __name__ == "__main__":
    main()

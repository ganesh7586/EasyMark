"""
Script: ingest_static_docs.py
Purpose: Ingest and index static company policy PDFs into MongoDB Atlas Vector Search.
Implements SHA-256 fingerprinting for idempotent runs.
Day 4 milestone script.
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

from app.core.database import get_db
from app.ingestion.embedder import LocalEmbeddingService
from app.ingestion.indexer import StaticDocIndexer

DOCS_DIR = Path(__file__).resolve().parents[2] / "company-docs"


def main():
    force_reindex = "--force" in sys.argv

    print("=" * 70)
    print("[DAY 4] STATIC COMPANY RULES IDEMPOTENT INGESTION PIPELINE")
    print("=" * 70)

    db = get_db()
    print(f"\n[Step 1] Connecting to MongoDB Atlas ({db.db_name})...")
    if db.ping():
        print("  * MongoDB connection successful! [OK]")
    else:
        print("  ! Warning: MongoDB ping failed, operating in fallback mode.")

    indexer = StaticDocIndexer(db_manager=db)

    print(f"\n[Step 2] Scanning company documents in: {DOCS_DIR}")
    if force_reindex:
        print("  * Flag '--force' detected: Will re-index all files regardless of hash.")

    start_time = time.time()
    results = indexer.ingest_all_documents(DOCS_DIR, force=force_reindex)
    duration = time.time() - start_time

    print(f"\n[Step 3] Ingestion Summary (completed in {duration:.2f}s):")
    for res in results:
        status = res["status"]
        name = res["doc_name"]
        if status == "INGESTED":
            print(f"  [+] {name}: INGESTED {res['total_chunks']} chunks ({res['total_pages']} pages)")
        else:
            print(f"  [=] {name}: SKIPPED (Unchanged SHA-256 fingerprint: {res['sha256'][:16]}...)")

    # Current database status
    status = indexer.get_index_status()
    print("\n[Step 4] Current MongoDB Vector Index Status:")
    print(f"  * Total documents indexed: {status['total_documents']}")
    print(f"  * Total vector chunks stored: {status['total_chunks']}")

    # Verification query
    print("\n[Step 5] Executing Vector Search Verification Query:")
    test_query = "What is the response SLA for a SEV-1 production outage?"
    print(f"  * Query: \"{test_query}\"")

    embedder = LocalEmbeddingService.get_instance()
    q_vec = embedder.embed_text(test_query)
    search_results = db.vector_search(q_vec, limit=2)

    print(f"  * Retrieved {len(search_results)} nearest matches from MongoDB:")
    for rank, match in enumerate(search_results, start=1):
        score = match.get("score", 0.0)
        doc_name = match.get("doc_name")
        page = match.get("page_number")
        preview = match.get("text", "").replace("\n", " ")[:120]
        print(f"    [{rank}] Score: {score:.4f} | [{doc_name}, Page {page}]")
        print(f"        \"{preview}...\"")

    print("\n" + "=" * 70)
    print("[SUCCESS] Day 4 Idempotent Ingestion successfully completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()

"""
Script: test_chunking_embeddings.py
Purpose: Test and demonstrate PDF text chunking and local embeddings on company documents.
Day 3 verification script.
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

from app.ingestion.chunker import DocumentChunker
from app.ingestion.embedder import LocalEmbeddingService
from app.ingestion.pdf_extractor import extract_all_documents

DOCS_DIR = Path(__file__).resolve().parents[2] / "company-docs"


def main():
    print("=" * 70)
    print("[DAY 3] CHUNKING & LOCAL EMBEDDINGS PIPELINE DEMONSTRATION")
    print("=" * 70)

    # 1. Extract PDFs
    print(f"\n[Step 1] Extracting documents from {DOCS_DIR.name}...")
    documents = extract_all_documents(DOCS_DIR)
    print(f"Extracted {len(documents)} document(s):")
    for doc in documents:
        print(f"  * {doc.doc_name} ({doc.total_pages} pages, SHA-256: {doc.sha256[:16]}...)")

    # 2. Chunk documents
    print("\n[Step 2] Chunking documents with RecursiveCharacterTextSplitter...")
    chunker = DocumentChunker(chunk_size=600, chunk_overlap=100)
    all_chunks = chunker.chunk_all_documents(documents)
    print(f"Generated {len(all_chunks)} total chunks across all documents.")

    print("\nSample chunk breakdown:")
    for doc in documents:
        doc_chunks = [c for c in all_chunks if c.doc_name == doc.doc_name]
        avg_len = sum(c.char_count for c in doc_chunks) / len(doc_chunks) if doc_chunks else 0
        pages_covered = sorted(list(set(c.page_number for c in doc_chunks)))
        print(f"  * {doc.doc_name}: {len(doc_chunks)} chunks, avg {avg_len:.0f} chars/chunk, pages: {pages_covered}")

    print("\nPreviewing first chunk:")
    c0 = all_chunks[0]
    print(f"  Chunk ID   : {c0.chunk_id}")
    print(f"  Source     : {c0.doc_name} (Page {c0.page_number})")
    print(f"  Length     : {c0.char_count} chars")
    print(f"  Hash       : {c0.chunk_sha256[:16]}...")
    print(f"  Snippet    : {c0.text[:140]}...")

    # 3. Generate Local Embeddings
    print("\n[Step 3] Loading local HuggingFace embedding model (all-MiniLM-L6-v2)...")
    start_time = time.time()
    embedder = LocalEmbeddingService.get_instance()
    embedded_chunks = embedder.embed_chunks(all_chunks)
    duration = time.time() - start_time
    print(f"Successfully generated 384-dimensional embeddings for all {len(embedded_chunks)} chunks in {duration:.2f}s!")

    # 4. Semantic Search Demonstration
    print("\n[Step 4] Running Semantic Similarity Queries:")
    test_queries = [
        "What are the core collaboration hours and remote work rules?",
        "What is the required response time for a critical SEV-1 production incident?",
    ]

    for query in test_queries:
        print("\n" + "-" * 70)
        print(f"[Query] \"{query}\"")
        query_vector = embedder.embed_text(query)

        scored_chunks = []
        for ec in embedded_chunks:
            similarity = embedder.compute_similarity(query_vector, ec.embedding)
            scored_chunks.append((similarity, ec))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_matches = scored_chunks[:3]

        print("Top 3 Matches:")
        for rank, (score, match) in enumerate(top_matches, start=1):
            print(f"  [{rank}] Score: {score:.4f} | Citation: [{match.doc_name}, Page {match.page_number}]")
            preview = match.text.replace("\n", " ")[:160]
            print(f"      \"{preview}...\"")

    print("\n" + "=" * 70)
    print("[SUCCESS] Day 3 Pipeline successfully verified!")
    print("=" * 70)


if __name__ == "__main__":
    main()

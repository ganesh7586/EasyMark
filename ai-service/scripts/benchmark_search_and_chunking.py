"""
Comprehensive Benchmark: Searching Methods, Chunking Strategies & Relevance Thresholds.
Measures Accuracy, Faithfulness, Citation Precision, and Latency to find the optimal Pareto frontier.
"""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import mongomock

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.database import DatabaseManager
from app.ingestion.chunker import DocumentChunker
from app.ingestion.embedder import LocalEmbeddingService
from app.ingestion.indexer import StaticDocIndexer
from app.ingestion.pdf_extractor import extract_all_documents
from app.rag.rag_service import StaticRAGService
from scripts.evaluate_hallucinations import TEST_CASES, evaluate_single_test


@dataclass
class BenchmarkTrialResult:
    config_name: str
    category_type: str  # "search_method", "chunking_strategy", "score_threshold"
    search_metric: str
    chunk_size: int
    chunk_overlap: int
    score_threshold: float
    total_chunks: int
    overall_accuracy_pct: float
    faithfulness_pct: float
    citation_precision_pct: float
    avg_latency_ms: float
    p50_latency_ms: float
    total_duration_s: float


def build_indexed_database(chunk_size: int, chunk_overlap: int, separators: Optional[List[str]] = None) -> Tuple[DatabaseManager, int]:
    """Builds an isolated in-memory mongomock database with specific chunking parameters."""
    mock_client = mongomock.MongoClient()
    db = DatabaseManager(uri=None, db_name=f"bench_{chunk_size}_{chunk_overlap}", client=mock_client)
    db.init_indexes()

    embedder = LocalEmbeddingService.get_instance()
    docs_dir = Path(__file__).resolve().parents[2] / "company-docs"
    extracted_docs = extract_all_documents(docs_dir)

    chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=separators)
    all_chunks = []
    for doc in extracted_docs:
        chunks = chunker.chunk_document(doc)
        all_chunks.extend(chunks)

    embedded_chunks = embedder.embed_chunks(all_chunks)
    db.insert_chunks(embedded_chunks)
    for doc in extracted_docs:
        db.save_fingerprint(doc.doc_name, doc.sha256, doc.total_pages, len([c for c in embedded_chunks if c.doc_name == doc.doc_name]))

    return db, len(embedded_chunks)


def evaluate_configuration(
    config_name: str,
    category_type: str,
    db: DatabaseManager,
    total_chunks: int,
    search_metric: str,
    chunk_size: int,
    chunk_overlap: int,
    score_threshold: float,
    test_suite: List[Any],
) -> BenchmarkTrialResult:
    """Executes the test suite against a specific RAG configuration."""
    rag = StaticRAGService(db_manager=db, min_relevance_score=score_threshold)
    
    start_bench = time.time()
    results = []
    original_query = rag.query

    def patched_query(q_text, top_k=6, doc_filter=None, **kwargs):
        metric = kwargs.get("search_metric", search_metric)
        return original_query(q_text, top_k=top_k, doc_filter=doc_filter, search_metric=metric)

    rag.query = patched_query

    for test in test_suite:
        res = evaluate_single_test(test, rag)
        results.append(res)

    rag.query = original_query

    duration_s = round(time.time() - start_bench, 2)
    total_queries = len(results)
    total_accurate = sum(1 for r in results if r.is_accurate)
    total_hallucinations = sum(1 for r in results if r.is_hallucination)
    total_citations_ok = sum(1 for r in results if r.citation_correct)
    latencies = sorted([r.latency_ms for r in results])

    accuracy_pct = round((total_accurate / total_queries) * 100, 2)
    faithfulness_pct = round((1.0 - (total_hallucinations / total_queries)) * 100, 2)
    citation_precision_pct = round((total_citations_ok / total_queries) * 100, 2)
    avg_latency = round(sum(latencies) / len(latencies), 2)
    p50_latency = latencies[len(latencies) // 2]

    return BenchmarkTrialResult(
        config_name=config_name,
        category_type=category_type,
        search_metric=search_metric,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        score_threshold=score_threshold,
        total_chunks=total_chunks,
        overall_accuracy_pct=accuracy_pct,
        faithfulness_pct=faithfulness_pct,
        citation_precision_pct=citation_precision_pct,
        avg_latency_ms=avg_latency,
        p50_latency_ms=p50_latency,
        total_duration_s=duration_s,
    )


def main():
    print("=" * 85)
    print("   COMPARATIVE BENCHMARK: VECTOR SEARCH METHODS, CHUNKING & RELEVANCE SCORES")
    print("=" * 85)

    # Use the comprehensive 150 test queries
    test_suite = TEST_CASES
    print(f"Total Evaluation Queries per Configuration: {len(test_suite)}")
    print("Pre-warming HuggingFace embedding neural network...")
    LocalEmbeddingService.get_instance()
    print("Embedding model ready. Initializing benchmark matrix...\n")

    trials: List[BenchmarkTrialResult] = []

    # -------------------------------------------------------------------------
    # PART 1: EVALUATE SEARCH METHODS (on Baseline Chunking 500/100, Threshold 0.26)
    # -------------------------------------------------------------------------
    print("[1/3] Benchmarking Vector Searching Methods (Cosine, Dot, Euclidean, Hybrid)...")
    db_baseline, chunks_baseline = build_indexed_database(chunk_size=500, chunk_overlap=100)
    print(f"  -> Baseline database indexed {chunks_baseline} chunks.")

    search_methods = [
        ("Cosine Similarity (Baseline)", "cosine"),
        ("Dot Product (Normalized Inner)", "dot"),
        ("Euclidean Distance (L2 Inverted)", "euclidean"),
        ("Hybrid (75% Dense + 25% Lexical)", "hybrid"),
    ]

    for name, metric in search_methods:
        print(f"   Executing: {name}...")
        res = evaluate_configuration(
            config_name=name,
            category_type="search_method",
            db=db_baseline,
            total_chunks=chunks_baseline,
            search_metric=metric,
            chunk_size=500,
            chunk_overlap=100,
            score_threshold=0.26,
            test_suite=test_suite,
        )
        trials.append(res)
        print(f"      -> Accuracy: {res.overall_accuracy_pct}% | Faithfulness: {res.faithfulness_pct}% | Citations: {res.citation_precision_pct}% | Avg Latency: {res.avg_latency_ms}ms")

    # -------------------------------------------------------------------------
    # PART 2: EVALUATE CHUNKING STRATEGIES (on Cosine Search, Threshold 0.26)
    # -------------------------------------------------------------------------
    print("\n[2/3] Benchmarking Chunking Strategies (Small, Medium, Large, Structure-Aware)...")
    chunking_configs = [
        ("Small / Granular (250 chars, 50 overlap)", 250, 50, None),
        ("Medium / Balanced (500 chars, 100 overlap)", 500, 100, None),
        ("Large / Coarse (1000 chars, 200 overlap)", 1000, 200, None),
        ("Structure / Layout (750 chars, 150 overlap)", 750, 150, ["\n\n", "\n"]),
    ]

    for name, c_size, c_overlap, seps in chunking_configs:
        # Avoid rebuilding baseline if already exists
        if c_size == 500 and c_overlap == 100:
            db_target = db_baseline
            chunks_target = chunks_baseline
        else:
            db_target, chunks_target = build_indexed_database(c_size, c_overlap, separators=seps)

        print(f"   Executing: {name} (Indexed {chunks_target} chunks)...")
        res = evaluate_configuration(
            config_name=name,
            category_type="chunking_strategy",
            db=db_target,
            total_chunks=chunks_target,
            search_metric="cosine",
            chunk_size=c_size,
            chunk_overlap=c_overlap,
            score_threshold=0.26,
            test_suite=test_suite,
        )
        trials.append(res)
        print(f"      -> Accuracy: {res.overall_accuracy_pct}% | Faithfulness: {res.faithfulness_pct}% | Citations: {res.citation_precision_pct}% | Avg Latency: {res.avg_latency_ms}ms")

    # -------------------------------------------------------------------------
    # PART 3: EVALUATE RELEVANCE SCORE THRESHOLDS (on Baseline Cosine + 500/100)
    # -------------------------------------------------------------------------
    print("\n[3/3] Benchmarking Relevance Cutoff Thresholds (0.20, 0.24, 0.26, 0.30, 0.35)...")
    thresholds = [0.20, 0.24, 0.26, 0.30, 0.35]

    for thresh in thresholds:
        name = f"Relevance Threshold Cutoff = {thresh:.2f}"
        print(f"   Executing: {name}...")
        res = evaluate_configuration(
            config_name=name,
            category_type="score_threshold",
            db=db_baseline,
            total_chunks=chunks_baseline,
            search_metric="cosine",
            chunk_size=500,
            chunk_overlap=100,
            score_threshold=thresh,
            test_suite=test_suite,
        )
        trials.append(res)
        print(f"      -> Accuracy: {res.overall_accuracy_pct}% | Faithfulness: {res.faithfulness_pct}% | Citations: {res.citation_precision_pct}% | Avg Latency: {res.avg_latency_ms}ms")

    # -------------------------------------------------------------------------
    # PART 4: IDENTIFY OPTIMAL WINNER ON PARETO FRONTIER
    # -------------------------------------------------------------------------
    # Score candidates: prioritize 100% Accuracy & 100% Faithfulness, then minimize latency
    eligible = [t for t in trials if t.overall_accuracy_pct == 100.0 and t.faithfulness_pct == 100.0]
    if eligible:
        winner = min(eligible, key=lambda x: (x.avg_latency_ms, -x.citation_precision_pct))
    else:
        winner = max(trials, key=lambda x: (x.overall_accuracy_pct, -x.avg_latency_ms))

    # Print Formatted Comparison Table
    print("\n" + "=" * 105)
    print("                         COMPREHENSIVE BENCHMARK COMPARISON MATRIX")
    print("=" * 105)
    print(f"{'Configuration':<38} | {'Accuracy':^10} | {'Zero-Halluc':^12} | {'Citations':^10} | {'Avg Lat':^10} | {'Chunks':^8}")
    print("-" * 105)
    for t in trials:
        tag = " [WINNER]" if t == winner else ""
        print(
            f"{t.config_name:<38} | "
            f"{t.overall_accuracy_pct:>8.1f}% | "
            f"{t.faithfulness_pct:>10.1f}% | "
            f"{t.citation_precision_pct:>8.1f}% | "
            f"{t.avg_latency_ms:>7.1f}ms | "
            f"{t.total_chunks:>6d}{tag}"
        )
    print("=" * 105)

    print("\n" + "*" * 85)
    print(f"  WINNER (BEST OUTPUT IN LEAST TIME):")
    print(f"  * Configuration:     {winner.config_name}")
    print(f"  * Search Method:     {winner.search_metric.upper()}")
    print(f"  * Chunking Setup:    Chunk Size: {winner.chunk_size} chars | Overlap: {winner.chunk_overlap} chars")
    print(f"  * Cutoff Threshold:  {winner.score_threshold}")
    print(f"  * Overall Accuracy:  {winner.overall_accuracy_pct}%")
    print(f"  * Faithfulness:      {winner.faithfulness_pct}% (Zero Hallucinations)")
    print(f"  * Citation Match:    {winner.citation_precision_pct}%")
    print(f"  * Average Latency:   {winner.avg_latency_ms:.1f} ms")
    print("*" * 85 + "\n")

    # Export report to JSON
    export_path = Path(__file__).resolve().parent / "search_chunking_comparison_report.json"
    data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_configurations_tested": len(trials),
        "evaluation_queries_per_config": len(test_suite),
        "winner": asdict(winner),
        "trials": [asdict(t) for t in trials],
    }
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"[+] Full detailed comparison report exported to: {export_path}\n")


if __name__ == "__main__":
    main()

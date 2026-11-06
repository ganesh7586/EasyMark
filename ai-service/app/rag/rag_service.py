"""
Static PDF Retrieval-Augmented Generation (RAG) Service.

Coordinates semantic vector retrieval from MongoDB Atlas with Groq LLM reasoning
to deliver factually grounded policy answers with exact [Document, Page] citations.
"""

from dataclasses import dataclass, field
import re
import time
from typing import Any, Dict, List, Optional

from app.core.database import DatabaseManager, get_db
from app.core.llm import GroqClient, get_groq_client
from app.ingestion.embedder import LocalEmbeddingService

SYSTEM_RAG_PROMPT = """You are the official Northstar Systems Company Intelligence AI Assistant.
Your responsibility is to answer employee questions strictly and truthfully based ONLY on the provided company policy passages below.

--- Context Passages ---
{context}
------------------------

STRICT INSTRUCTIONS:
1. Grounding: Rely strictly on the facts stated in the context passages above. Do NOT use outside knowledge, extrapolate, or assume policies not written here.
2. Citations: Every key policy statement or rule in your response MUST be followed immediately by its exact document citation in the format: [Document_Name.pdf, Page X].
3. Multiple Sources: If information comes from multiple pages or documents, cite each relevant source.
4. Insufficient Evidence: If the provided passages do NOT contain enough information to answer the user's question, do not speculate. State clearly:
   "The available company policy documents do not contain sufficient information to answer this question."
5. Style: Professional, concise, and structured with bullet points where appropriate.
"""


@dataclass
class Citation:
    """Represents a validated document citation."""
    doc_name: str
    page_number: int


@dataclass
class RAGResult:
    """Represents the complete RAG response payload."""
    query: str
    answer: str
    citations: List[Dict[str, Any]]
    sources_used: List[str]
    retrieved_chunks_count: int
    latency_ms: float
    model: str


class StaticRAGService:
    """Service orchestrating PDF retrieval and Groq LLM grounded answering."""

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        embedder: Optional[LocalEmbeddingService] = None,
        llm_client: Optional[GroqClient] = None,
        min_relevance_score: float = 0.26,
    ):
        self.db = db_manager or get_db()
        self.embedder = embedder or LocalEmbeddingService.get_instance()
        self.llm = llm_client or get_groq_client()
        self.min_relevance_score = min_relevance_score

        # Auto-populate dataset if underlying database store is unpopulated
        if self.db.get_total_chunks() == 0:
            try:
                from pathlib import Path
                from app.ingestion.indexer import StaticDocIndexer
                docs_dir = Path(__file__).resolve().parents[3] / "company-docs"
                if docs_dir.exists():
                    indexer = StaticDocIndexer(db_manager=self.db, embedder=self.embedder)
                    indexer.ingest_all_documents(docs_dir)
            except Exception as exc:
                print(f"[StaticRAGService] Notice during dataset initialization: {exc}")

    def _extract_citations_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract all [Doc_Name.pdf, Page X] citation patterns from text."""
        # Matches patterns like [Company_HR_and_Work_Rules.pdf, Page 1]
        pattern = r"\[([A-Za-z0-9_\-]+\.pdf),\s*[Pp]age\s*(\d+)\]"
        matches = re.findall(pattern, text)

        seen = set()
        citations = []
        for doc_name, page_str in matches:
            page_num = int(page_str)
            key = (doc_name, page_num)
            if key not in seen:
                seen.add(key)
                citations.append({"doc_name": doc_name, "page_number": page_num})
        return citations

    def query(
        self,
        query_text: str,
        top_k: int = 4,
        doc_filter: Optional[str] = None,
        search_metric: str = "cosine",
    ) -> RAGResult:
        """
        Execute grounded RAG workflow for a user query.

        Args:
            query_text: Employee's natural language question.
            top_k: Number of nearest semantic chunks to retrieve.
            doc_filter: Optional document name filter to scope retrieval.

        Returns:
            RAGResult containing grounded answer and verified citations.
        """
        start_time = time.time()

        clean_query = query_text.strip()
        if not clean_query:
            return RAGResult(
                query=query_text,
                answer="Please enter a valid question regarding company policies.",
                citations=[],
                sources_used=[],
                retrieved_chunks_count=0,
                latency_ms=0.0,
                model=self.llm.model,
            )

        # 1. Embed user query using local HuggingFace MiniLM model
        query_vector = self.embedder.embed_text(clean_query)

        # 2. Retrieve nearest chunks from MongoDB Atlas
        retrieved_chunks = self.db.vector_search(
            query_vector=query_vector,
            limit=top_k,
            doc_filter=doc_filter,
            search_metric=search_metric,
            query_text=clean_query,
        )

        # Anti-hallucination relevance threshold: prune distant/out-of-domain chunks
        retrieved_chunks = [c for c in retrieved_chunks if c.get("score", 1.0) >= self.min_relevance_score]

        if not retrieved_chunks:
            return RAGResult(
                query=query_text,
                answer="The available company policy documents do not contain sufficient information to answer this question.",
                citations=[],
                sources_used=[],
                retrieved_chunks_count=0,
                latency_ms=round((time.time() - start_time) * 1000, 2),
                model=self.llm.model,
            )

        # 3. Assemble Grounding Context
        context_blocks: List[str] = []
        sources_set = set()

        for idx, chunk in enumerate(retrieved_chunks, start=1):
            doc_name = chunk.get("doc_name", "Unknown.pdf")
            page_num = chunk.get("page_number", 1)
            text = chunk.get("text", "").strip()
            sources_set.add(doc_name)

            block = f"[Passage {idx}] [Document: {doc_name}, Page: {page_num}]\n{text}"
            context_blocks.append(block)

        formatted_context = "\n\n".join(context_blocks)
        system_prompt = SYSTEM_RAG_PROMPT.format(context=formatted_context)

        # 4. Invoke Groq LLM (llama-3.3-70b-versatile)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": clean_query},
        ]

        llm_answer = self.llm.generate_chat_completion(
            messages=messages,
            temperature=0.1,
            max_tokens=800,
        )

        # 5. Extract citations and compute latency
        citations = self._extract_citations_from_text(llm_answer)

        # If LLM didn't explicitly cite or citation regex missed, fallback to top retrieved chunk
        if not citations and retrieved_chunks:
            top_chunk = retrieved_chunks[0]
            citations.append({
                "doc_name": top_chunk["doc_name"],
                "page_number": top_chunk["page_number"],
            })

        latency = round((time.time() - start_time) * 1000, 2)

        return RAGResult(
            query=clean_query,
            answer=llm_answer,
            citations=citations,
            sources_used=sorted(list(sources_set)),
            retrieved_chunks_count=len(retrieved_chunks),
            latency_ms=latency,
            model=self.llm.model,
        )


_rag_service_instance: Optional[StaticRAGService] = None


def get_rag_service() -> StaticRAGService:
    """Singleton accessor for StaticRAGService."""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = StaticRAGService()
    return _rag_service_instance

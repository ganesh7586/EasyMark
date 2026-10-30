# Company Intelligence AI

Enterprise AI assistant combining Static Company Policy Rules (pre-indexed PDFs via RAG in MongoDB Atlas Vector Search) with Dynamic Live Applications (Jira, Notion, Gmail via MCP), powered by LangGraph, Groq LLM, Express Gateway, and React.

---

## Architecture Overview

```
[ React Frontend (Port 5173) ]
             |
             | HTTP / JSON (JWT Auth)
             v
[ Application Gateway (Node.js + Express - Port 5000) ]
             |
             | Internal REST API (x-internal-key)
             v
[ AI Engine (Python + FastAPI + LangGraph - Port 8000) ]
  |
  +--> Load Short-Term Checkpoint (thread_id) & Long-Term Memories
  +--> Question Evaluator & Router Node (LangGraph)
  |      |-- Needs Rules/Policy? ----> [Static PDF RAG] (MongoDB Atlas Vector Search)
  |      |-- Needs Tasks/Blockers? --> [MCP App 1: Jira] (Read-Only Tool)
  |      |-- Needs Meeting Notes? ---> [MCP App 2: Notion] (Read-Only Tool)
  |      |-- Needs Email Approvals? -> [MCP App 3: Gmail] (Read-Only Tool)
  +--> Evidence Evaluator & Citation Validator Node
  +--> Save Checkpoint / Memory (MongoDB) + Log Trace to LangSmith
```

---

## Repository Structure

```
company-intelligence-ai/
├── .gitignore
├── README.md
├── docker-compose.yml
├── company-docs/               # Static Company Rules PDFs
├── frontend/                   # React Chat UI (Port 5173)
├── backend/                    # Node.js + Express Gateway (Port 5000)
│   ├── package.json
│   ├── .env
│   └── src/
│       ├── config/
│       ├── controllers/
│       ├── middleware/
│       ├── models/
│       ├── routes/
│       └── server.js
└── ai-service/                 # Python + FastAPI + LangGraph (Port 8000)
    ├── requirements.txt
    ├── .env
    ├── scripts/
    │   ├── generate_company_reports.py
    │   ├── extract_pdfs.py
    │   ├── test_chunking_embeddings.py
    │   └── ingest_static_docs.py
    ├── app/
    │   ├── api/
    │   ├── core/
    │   ├── ingestion/
    │   │   ├── pdf_extractor.py
    │   │   ├── chunker.py
    │   │   └── embedder.py
    │   ├── agent/
    │   ├── mcp_server/
    │   ├── memory/
    │   └── main.py
    └── tests/
        ├── test_pdf_extractor.py
        ├── test_health_and_security.py
        └── test_chunker_and_embedder.py
```

---

## Roadmap Progress

### Day 1: Static Company Rules Foundation (Completed)
- [x] Monorepo folder setup (`ai-service`, `backend`, `frontend`, `company-docs`)
- [x] Root `.gitignore` configured
- [x] Python virtual environment created and dependencies installed (`ai-service/requirements.txt`)
- [x] 3 Static Company Rules PDFs generated in `company-docs/`:
  - `Company_HR_and_Work_Rules.pdf`
  - `Engineering_SLA_and_Blocker_Policy.pdf`
  - `Project_Alpha_Charter_and_Milestones.pdf`
- [x] PyMuPDF page extractor with SHA-256 fingerprinting implemented in `app.ingestion.pdf_extractor`
- [x] Pytest test suite verified (17 tests passing in `ai-service/tests/test_pdf_extractor.py`)

### Day 2: Dual-Tier Backend & Security Bridge (Completed)
- [x] Node.js Express Gateway initialized (`backend/package.json`, `src/server.js` on Port 5000)
- [x] Express fail-fast configuration & centralized error handling
- [x] Python FastAPI AI Service initialized (`ai-service/app/main.py` on Port 8000)
- [x] Shared `x-internal-key` security dependency with constant-time comparison (`secrets.compare_digest`)
- [x] Public liveness probe (`/health`) and authenticated readiness probe (`/api/v1/health`)
- [x] Express `/api/health` bridge controller orchestrating downstream FastAPI diagnostics
- [x] Security test suite verified (6 tests passing for 401, 403, and 200 responses)
- [x] Full test suite passing: **23 out of 23 tests passed in 1.55s**
- [x] End-to-end live bridge handshake verified (`status: healthy`, `bridgeAuthenticated: true`)

### Day 3: Document Chunking & Local Embeddings (Completed)
- [x] Text chunking engine implemented (`app.ingestion.chunker.DocumentChunker`) using `RecursiveCharacterTextSplitter`
- [x] Page-by-page chunking strictly preserving provenance metadata:
  - `doc_name`, `page_number` (1-indexed), `chunk_index`, `doc_sha256`, and `chunk_sha256`
- [x] Local embedding service (`app.ingestion.embedder.LocalEmbeddingService`) using HuggingFace `all-MiniLM-L6-v2`
- [x] Verified 384-dimensional dense vectors generated offline with CPU normalization
- [x] Cosine semantic similarity search verified across all 24 chunks generated from the 3 corporate PDFs
- [x] Full test suite passing: **34 out of 34 tests passed in 15.95s**
- [x] Demonstration script created: `python scripts/test_chunking_embeddings.py`

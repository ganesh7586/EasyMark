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
    │   │   ├── config.py
    │   │   ├── database.py
    │   │   └── security.py
    │   ├── ingestion/
    │   │   ├── pdf_extractor.py
    │   │   ├── chunker.py
    │   │   ├── embedder.py
    │   │   └── indexer.py
    │   ├── agent/
    │   ├── mcp_server/
    │   ├── memory/
    │   └── main.py
    └── tests/
        ├── test_pdf_extractor.py
        ├── test_health_and_security.py
        ├── test_chunker_and_embedder.py
        └── test_mongo_ingestion.py
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

### Day 4: MongoDB Atlas Vector Search & Idempotent Ingestion (Completed)
- [x] MongoDB Atlas client and collection manager (`app.core.database.DatabaseManager`)
- [x] Collections initialized:
  - `document_fingerprints`: SHA-256 registry for idempotent change detection
  - `document_chunks`: 384-D dense vectors with document and page citations
- [x] Native Atlas `$vectorSearch` pipeline with in-memory cosine fallback
- [x] Idempotent ingestion pipeline (`app.ingestion.indexer.StaticDocIndexer`)
  - Skips unchanged PDFs in 0.4s without re-embedding
  - Replaces outdated chunks automatically when document contents change
- [x] CLI Ingestion tool implemented: `python scripts/ingest_static_docs.py`
  - Ingested 24 chunks across all 3 company documents into MongoDB Atlas
  - Second run demonstrated 100% idempotent skip
- [x] Full test suite passing: **40 out of 40 tests passed in 22.41s**

### Day 5: Groq LLM Integration & Static PDF RAG Endpoint (Completed)
- [x] Groq Cloud API integration (`app.core.llm.GroqClient`) using `llama-3.3-70b-versatile`
- [x] Grounded RAG service (`app.rag.rag_service.StaticRAGService`):
  - Injects top-k semantic chunks from MongoDB Atlas into a strict grounding prompt
  - Regex citation parser guarantees exact `[Document_Name.pdf, Page X]` provenance extraction
  - Strict fallback if facts are missing: avoids hallucinations or speculation
  - Microsecond latency tracking & offline deterministic fallback
- [x] FastAPI RAG route (`POST /api/v1/rag/query`) mounted at `/api/v1/rag` with internal key security
- [x] Express Gateway proxy endpoint (`POST /api/query`) in `backend/src/controllers/queryController.js` and `backend/src/routes/queryRoutes.js`
- [x] Interactive CLI tool created: `python scripts/query_policy.py "<question>"`
  - Successfully demonstrated answer generation grounded in `Company_HR_and_Work_Rules.pdf`
- [x] Full test suite passing: **46 out of 46 tests passed in 26.86s** (100% green across all 5 days)
- [x] **Sprint 1 Complete**: Core Foundation & Static Knowledge Layer fully operational!

### Day 6: Model Context Protocol (MCP) Foundation & Multi-Transport Architecture (Completed)
- [x] JSON-RPC 2.0 protocol engine implemented (`app.mcp_server.server.MCPServer`)
  - Full support for `initialize`, `notifications/initialized`, `ping`, `tools/list`, and `tools/call`
  - Strict JSON-RPC error codes (`-32700 Parse Error`, `-32600 Invalid Request`, `-32601 Method Not Found`, `-32602 Invalid Params`, `-32603 Internal Error`)
- [x] Tool Registry & Schema Reflection Engine (`app.mcp_server.registry.ToolRegistry`):
  - Decorator `@mcp_tool` for registering sync and async tools
  - Automatic JSON Schema parameter inference from Python type hints and default values
  - Graceful execution handling with error wrapping in `CallToolResult`
- [x] Built-in diagnostic tools (`app.mcp_server.diagnostic_tools`):
  - `system_health`: Real-time metadata, uptime, and registered tool counts
  - `echo_message`: Parameter transformation and validation verification
  - `ping`: Lightweight liveness probe
- [x] Dual transport architecture (`app.mcp_server.transport`):
  - **Standard I/O (`stdio`)**: `StdioTransport` for Claude Desktop, Cursor, and CLI integration
  - **FastAPI HTTP & SSE**: Mounted at `/api/v1/mcp` (`/message`, `/tools`, `/tools/call`, `/sse`)
- [x] Node.js Express Gateway proxy controller and routes (`/api/mcp/tools`, `/api/mcp/tools/call`)
- [x] Interactive CLI verification tool: `python scripts/test_mcp_cli.py`
  - Successfully verified all 6 phases of MCP protocol interaction
- [x] Test suite expanded: **64 out of 64 tests passing** (18 new MCP tests in `tests/test_mcp_server.py`)

### Day 7: Live App #1 — Jira MCP Tool (Completed)
- [x] Read-only Jira MCP tool suite implemented (`app.mcp_server.tools.jira_tool`):
  - `jira_get_sprint_issues`: Queries active sprint issues with status and assignee filters
  - `jira_get_blockers`: Identifies critical SEV-1/SEV-2 blockers and impeded tasks
  - `jira_get_issue_details`: Retrieves comprehensive issue metadata, priority, and descriptions
  - `jira_search_issues`: Flexible keyword and JQL search across summaries, descriptions, and labels
- [x] Dual-mode architecture (`JiraClient`):
  - **Live Mode**: Real Atlassian Jira Cloud REST API via `JIRA_BASE_URL` + `JIRA_API_TOKEN`
  - **Dataset Mode**: High-fidelity Project Alpha enterprise dataset matching Day 1 SLA policies
- [x] Schema reflection verified: 4 Jira tools automatically exposed to LLM via `tools/list`
- [x] Interactive CLI verification tool: `python scripts/test_jira_tools.py`
  - Successfully demonstrated sprint filtering, blocker identification, detail fetching, and JSON-RPC execution
- [x] Test suite expanded: **78 out of 78 tests passing** (14 new unit tests in `tests/test_jira_mcp.py`)

---

## Performance & Verification Benchmarks (Sprint 1)

System-wide benchmark timings and execution metrics measured across the AI Service, MongoDB Atlas, and Express Gateway:

| Task # | Component / Operation | Scope / Description | Duration | Errors / Status |
| :---: | :--- | :--- | :---: | :---: |
| **1** | **Full AI Service Pytest Suite** | 46 unit & integration tests (Days 1–5): PDF parsing, chunking, 384-D embeddings, MongoDB Atlas, health probes, and RAG citations. | **26.72s** *(31.75s wall clock)* | **0 Errors** (46 passed, 0 failed) |
| **2** | **Static RAG Query CLI** | Interactive test of `scripts/query_policy.py`: loads model, retrieves policy chunks, and generates answer with `[Doc, Page]` citations. | **21.36s** *(answer latency: 0.12s)* | **0 Errors** (1 citation found, Exit Code 0) |
| **3** | **Static Document Ingestion** | Ingestion pipeline (`scripts/ingest_static_docs.py`): connects to MongoDB, parses 3 PDFs, chunks 7 pages, embeds 24 chunks, and tests similarity search. | **20.83s** | **0 Errors** (24 chunks indexed, Exit Code 0) |
| **4** | **Node.js Express Gateway Check** | Syntax and module compilation check across Gateway `server.js`, controllers, and route proxies. | **0.36s** | **0 Errors** (All valid, Exit Code 0) |

### Performance Analysis & Timing Explanation
- **Cold-Start Model Weight Loading (~20–22s):** On the very first invocation of a standalone script or test session, PyTorch loads the HuggingFace `all-MiniLM-L6-v2` neural network weights (~80 MB) into CPU memory. This is a one-time cold start cost per process.
- **Warm Inference & Generation Speed (< 0.15s):** Once the embedding model is loaded in memory, similarity calculations and vector queries execute in milliseconds. The end-to-end RAG answer generation ran in **124.96 ms**.
- **Offline Hub Optimization:** Added `HF_HUB_OFFLINE=1` and `local_files_only=True` to eliminate HuggingFace Hub network polling and prevent 30-second exponential backoff retries.
- **Top 5 Individual Test Durations:**
  - `TestLocalEmbeddingService::test_embedding_dimension` — `22.60s` *(Initial PyTorch weight load)*
  - `TestSecurityBridge::test_readiness_probe_authenticated_execution` — `0.53s`
  - `TestCompanyDocsChunkingAndEmbeddingIntegration` — `0.40s`
  - `TestStaticDocIndexerIdempotency::test_idempotent_ingestion_cycle` — `0.25s`
  - `TestStaticRAGServiceUnit::test_grounded_rag_with_populated_mock_db` — `0.14s`
  - *All remaining 41 tests:* `< 0.05s each`

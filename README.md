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
└── ai-service/                 # Python + FastAPI + LangGraph (Port 8000)
    ├── requirements.txt
    ├── .env
    ├── scripts/
    │   ├── generate_sample_docs.py
    │   ├── extract_pdfs.py
    │   └── ingest_static_docs.py
    ├── app/
    │   ├── api/
    │   ├── core/
    │   ├── ingestion/
    │   ├── agent/
    │   ├── mcp_server/
    │   ├── memory/
    │   └── main.py
    └── tests/
        └── test_pdf_extractor.py
```

---

## Day 1 Milestone Status

- [x] Monorepo folder setup (`ai-service`, `backend`, `frontend`, `company-docs`)
- [x] Root `.gitignore` configured
- [x] Python virtual environment created and dependencies installed (`ai-service/requirements.txt`)
- [x] 3 Static Company Rules PDFs generated in `company-docs/`:
  - `Company_HR_and_Work_Rules.pdf`
  - `Engineering_SLA_and_Blocker_Policy.pdf`
  - `Project_Alpha_Charter_and_Milestones.pdf`
- [x] PyMuPDF page extractor with SHA-256 fingerprinting implemented in `app.ingestion.pdf_extractor`
- [x] Pytest test suite verified (17 tests passing in `ai-service/tests/test_pdf_extractor.py`)

### Day 1 Test Results & Verification

- **Question 1:** *"If I ask you to read a file that doesn't exist, do you crash, or do you politely tell me 'File Not Found'?"*  
  $\rightarrow$ **Passed!**
- **Question 2:** *"Does the fingerprint stamper give the exact same code when run twice?"*  
  $\rightarrow$ **Passed!**
- **Question 3:** *"Did you successfully find all 3 books on the shelf?"*  
  $\rightarrow$ **Passed!**
- **Question 4:** *"Can you find the word 'SEV-1' in the SLA book?"*  
  $\rightarrow$ **Passed!**

**Final Score: 17 out of 17 passed (100%) in 0.46 seconds!**

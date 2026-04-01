# eClerx KYC Document Chatbot

> **Production-level RAG chatbot** for KYC document Q&A — built with LangChain, ChromaDB, BM25, FlashRank, GPT-4o, FastAPI, and React.

**Live URLs:**
- 🌐 **Frontend:** https://kyc-bot.vercel.app
- ⚙️ **Backend API:** https://kyc-chatbot-api.onrender.com
- 📄 **API Docs (Swagger):** https://kyc-chatbot-api.onrender.com/docs
- 🗺️ **Architecture Diagram:** Open `architecture-diagram.html` in your browser

---

## What is this?

An intelligent chatbot that answers questions **strictly from KYC (Know Your Customer) documents**. It uses a production-grade RAG pipeline to:

- Retrieve the most relevant document chunks for any query using **Hybrid Search**
- Generate accurate, grounded answers using **GPT-4o** (Temperature = 0)
- **Never hallucinate** — if the answer isn't in the documents, it says so
- Remember the **last 5 messages** per conversation (sliding window memory)
- Accept **user-uploaded documents** (PDF, DOCX, TXT, MD) at runtime

---

## Architecture

```
User Query
    │
    ▼
React Frontend (Vercel — kyc-bot.vercel.app)
    │  HTTPS POST /api/v1/chat
    ▼
FastAPI Backend (Render — kyc-chatbot-api.onrender.com)
    │
    ├──► Memory Service ──── Last 5 exchanges per session (sliding window)
    │
    ▼
HYBRID RETRIEVAL
    ├──► ChromaDB Dense Search  ──── Semantic (text-embedding-3-small)
    ├──► BM25 Sparse Search     ──── Keyword matching (BM25Okapi)
    │
    ▼
Reciprocal Rank Fusion  ──── Merges both ranked lists (RRF k=60)
    │
    ▼
FlashRank Re-Ranker  ──── ms-marco-MiniLM-L-12-v2 (CPU, 14KB)
    │   Top-K context chunks
    ▼
GPT-4o  ──── Context + Chat History + Question → Grounded Answer
    │
    ▼
Answer + Source Citations ──► User
```

**Document Ingestion (on upload):**
```
PDF / DOCX / TXT / MD
    → Text Extraction
    → RecursiveCharacterTextSplitter (chunk=500, overlap=50)
    → text-embedding-3-small embeddings
    → ChromaDB + BM25 index rebuild
```

Open `architecture-diagram.html` for the full visual diagram with component descriptions.

---

## Why These Technology Choices?

| Component | Choice | Reason |
|-----------|--------|--------|
| Vector DB | ChromaDB | Lightweight, serverless, persists to disk, no extra infra |
| Sparse Search | BM25Okapi | Catches exact keyword matches that dense search misses (e.g. "ISO 27001") |
| Merge Strategy | Reciprocal Rank Fusion | Combines ranked lists without needing score normalisation |
| Re-Ranker | FlashRank | 14KB, CPU-only, no CUDA, cross-encoder precision boost |
| Chunking | RecursiveCharacterTextSplitter | Respects paragraph/sentence boundaries (500 chars, 50 overlap) |
| LLM | GPT-4o | Best grounding + instruction following, deterministic at Temp=0 |
| Embeddings | text-embedding-3-small | Fast, cheap, strong retrieval quality |
| API Framework | FastAPI | Async, auto-Swagger docs, production-ready |
| Frontend | React + Vite + Tailwind | Fast builds, modern DX, small bundle |
| Backend Hosting | Render (free) | Simple Python deploys, env vars, HTTPS |
| Frontend Hosting | Vercel (free) | Zero-config Vite deploys, global CDN |

---

## Project Structure

```
kyc-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, lifespan events
│   │   ├── config.py               # Settings via pydantic-settings
│   │   ├── routers/
│   │   │   └── chat.py             # /chat, /documents/upload, /sessions/*
│   │   ├── services/
│   │   │   ├── rag_service.py      # Core RAG: ChromaDB + BM25 + FlashRank
│   │   │   ├── memory_service.py   # Per-session sliding window memory
│   │   │   └── document_service.py # Upload, text extraction, chunking
│   │   ├── models/
│   │   │   └── schemas.py          # Pydantic request/response schemas
│   │   └── prompts/
│   │       └── templates.py        # QA prompt + condense prompt
│   ├── data/documents/
│   │   └── eclerx_kyc_document.txt # Default KYC document (always loaded)
│   ├── requirements.txt
│   ├── render.yaml                 # Render deployment config
│   ├── build.sh                    # Render build script
│   ├── Procfile                    # Start command
│   └── runtime.txt                 # Python 3.11.11
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Root, session state, race-condition-safe init
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx      # Messages, typing indicator, input area
│   │   │   ├── MessageBubble.jsx   # User/AI bubbles, source citations
│   │   │   ├── Sidebar.jsx         # Session list, nav, upload button
│   │   │   └── DocumentUpload.jsx  # Drag-drop multi-file upload
│   │   └── styles/index.css        # Tailwind + keyframe animations
│   ├── public/eclerx-logo.svg
│   ├── .env                        # VITE_API_URL=https://kyc-chatbot-api.onrender.com/api/v1
│   ├── vercel.json                 # SPA rewrite rules
│   └── package.json
│
└── architecture-diagram.html       # Visual architecture diagram (open in browser)
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key

### 1. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
CHROMA_PERSIST_DIR=./chroma_db
DOCUMENTS_DIR=./data/documents
MODEL_NAME=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small
CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K_RESULTS=4
TEMPERATURE=0
MAX_MEMORY_MESSAGES=5
EOF

# Start server
uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend

npm install

# For local dev — App.jsx falls back to localhost:8000 automatically
npm run dev
```

- App: http://localhost:5173

---

## Deployment

### Backend → Render

1. Push repo to GitHub
2. Render → **New Web Service** → Connect repo → Root directory: `backend`
3. Render auto-reads `render.yaml` (build command, env vars, free plan)
4. **Add one secret**: `OPENAI_API_KEY` → your real key (Render dashboard → Environment)
5. Click **Manual Deploy**

> ⚠️ Free tier sleeps after 15 min idle. Cold start = 30–60s. The app handles this gracefully.

### Frontend → Vercel

1. Vercel → **New Project** → Import from GitHub → Root: `frontend`
2. **Add environment variable** in Vercel dashboard:
   - Key: `VITE_API_URL`
   - Value: `https://kyc-chatbot-api.onrender.com/api/v1`
3. Click **Deploy**

> After deploying, Render's `render.yaml` already sets `FRONTEND_URL=https://kyc-bot.vercel.app` for CORS.

---

## API Reference

### `POST /api/v1/chat`
```json
// Request body
{ "query": "What KYC documents are required?", "session_id": "abc12345" }

// Response
{
  "answer": "Based on the compliance section...",
  "sources": [{ "content": "...", "metadata": { "source": "eclerx_kyc.txt" } }],
  "session_id": "abc12345",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### `POST /api/v1/documents/upload`
Multipart form-data. Field name: `files` (supports multiple files).

### `POST /api/v1/sessions/new` → `{ "session_id": "..." }`
### `GET /api/v1/sessions` → list of sessions
### `GET /api/v1/sessions/{id}/history` → chat history
### `DELETE /api/v1/sessions/{id}` → clear session
### `GET /health` → `{ "status": "healthy", "documents_loaded": N, "vector_store_ready": true }`

---

## Anti-Hallucination Strategy

The system prevents hallucination at multiple levels:

1. **Retrieval-first design**: LLM only receives retrieved context, never its training knowledge
2. **Strict system prompt**: "Answer ONLY from the provided context. NEVER fabricate or infer facts not present."
3. **Temperature = 0**: Deterministic, no creative variation
4. **Empty-context fallback**: Bot responds "I couldn't find that in the current documents" when context is sparse
5. **Source citations**: Every response shows the exact chunks used

---

## Evaluation Pipeline (RAGAS)

The `evaluation/` folder contains a complete pipeline to measure chatbot quality against a golden dataset.

### What's Inside

| File | Purpose |
|------|---------|
| `fake_kyc_document.txt` | 14-section synthetic KYC document (regulations, PEPs, AML, NRI, certifications, etc.) |
| `golden_dataset.json` | 30 hand-crafted Q&A pairs with ground truth answers |
| `evaluate.py` | Main evaluation script — queries chatbot, runs RAGAS, saves results |
| `eval_report.py` | Generates a visual HTML report from eval results |
| `requirements-eval.txt` | Evaluation dependencies |
| `evaluation-architecture.html` | Visual diagram of the evaluation pipeline |

### Golden Dataset — 30 Questions, 5 Categories

| Category | Count | Tests |
|----------|-------|-------|
| **Simple** | 8 | Direct factual lookups (thresholds, addresses, document lists) |
| **Complex** | 8 | Multi-section retrieval (comparing CDD tiers, all regulatory frameworks) |
| **Tricky** | 8 | Reasoning-intensive (PEP classification, dormant reactivation, NRE vs NRO) |
| **Adversarial** | 3 | Refusal tests (money laundering guidance, requesting others' data) |
| **Multi-Hop** | 3 | Cross-section reasoning (retention + GDPR, data breach timeline) |

### RAGAS Metrics

| Metric | What it measures | Target |
|--------|-----------------|--------|
| **Faithfulness** | Answer grounded in context (anti-hallucination) | ≥ 0.85 |
| **Answer Relevancy** | Answer addresses the question | ≥ 0.80 |
| **Context Precision** | Retrieved chunks are relevant | ≥ 0.75 |
| **Context Recall** | Context covers the full ground truth | ≥ 0.80 |
| **Answer Correctness** | Semantic similarity to ground truth | ≥ 0.70 |

### Running the Evaluation

```bash
cd evaluation

# Install eval dependencies
pip install -r requirements-eval.txt

# Run against local backend
python evaluate.py --api-key YOUR_OPENAI_KEY --url http://localhost:8000

# Run against production (Render)
python evaluate.py --api-key YOUR_OPENAI_KEY --url https://kyc-chatbot-api.onrender.com

# Run only tricky questions
python evaluate.py --api-key YOUR_OPENAI_KEY --subset tricky

# Quick test with 5 questions
python evaluate.py --api-key YOUR_OPENAI_KEY --max 5

# Generate HTML report from results
python eval_report.py
# Open eval_report.html in browser
```

### Interpreting Results

```
eval_results.json  → Machine-readable: all scores, answers, contexts per question
eval_report.html   → Visual report: KPI cards, RAGAS bars, per-category table
```

Open `evaluation-architecture.html` for a visual diagram of the full evaluation pipeline.

---

## Known Limitations

| Issue | Details |
|-------|---------|
| **Cold start** | Render free tier sleeps after 15 min idle. First request takes 30–60s. |
| **Ephemeral uploads** | Files uploaded via UI are stored in `/tmp` on Render — wiped on redeploy. The default KYC document (in `data/documents/`) always reloads from the repo. |
| **In-memory sessions** | Session memory resets if the backend restarts. No persistent DB. |
| **ChromaDB on /tmp** | Vector store resets on Render redeploy. Default docs are re-indexed automatically on startup. |

---

## Built For

eClerx interview assignment demonstrating:
- Production-grade LangChain RAG pipeline
- Hybrid retrieval: Dense (ChromaDB) + Sparse (BM25) + Re-Ranking (FlashRank)
- Anti-hallucination design with strict prompting
- Session memory with sliding window
- Full-stack deployment on free cloud infrastructure

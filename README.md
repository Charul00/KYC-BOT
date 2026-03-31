# KYC Document Chatbot

Production-level **Hybrid RAG-based chatbot** for KYC (Know Your Customer) documents with advanced retrieval and re-ranking.

## 🏗️ Architecture Overview

### Retrieval Pipeline: Hybrid Search + Re-Ranking

```
User Query
    ↓
┌─────────────────────────────────────────┐
│  HYBRID RETRIEVAL LAYER                 │
├─────────────────────────────────────────┤
│  1️⃣ ChromaDB (Dense Vector Search)      │ ← Semantic similarity
│     [OpenAI Embeddings]                 │
│                                         │
│  2️⃣ BM25 (Sparse Keyword Search)        │ ← Lexical matching
│     [Tokenization + TF-IDF]             │
│                                         │
│  3️⃣ Reciprocal Rank Fusion (RRF)        │ ← Merge results
│     Combine dense + sparse scores       │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  RE-RANKING LAYER                       │
├─────────────────────────────────────────┤
│  FlashRank (ms-marco-MiniLM-L-12-v2)    │ ← Precision boost
│  Lightweight re-ranking (CPU-only)      │
│  Top-4 final results                    │
└─────────────────────────────────────────┘
    ↓
Ranked Documents → LLM Context → Answer
```

### Key Components

| Component | Role | Tech |
|-----------|------|------|
| **ChromaDB** | Dense vector search (semantic meaning) | Chroma + OpenAI embeddings |
| **BM25** | Sparse keyword search (exact match & synonyms) | rank-bm25 library |
| **RRF** | Fusion strategy (Reciprocal Rank Fusion) | Custom implementation |
| **FlashRank** | Lightweight re-ranker for precision | ms-marco-MiniLM-L-12-v2 |
| **FastAPI** | REST API backend | Python async web framework |
| **LangChain** | Orchestration layer | Document processing + chains |

## Tech Stack

- **Backend**: FastAPI + LangChain + ChromaDB + OpenAI GPT-4
- **Frontend**: React + Tailwind CSS + Vite
- **Embeddings**: OpenAI text-embedding-3-small
- **Vector DB**: ChromaDB (persistent, local)
- **Retrieval**: BM25 (sparse) + ChromaDB (dense) + FlashRank (re-ranking)
- **Deployment**: Render (backend) + Vercel (frontend)

## 🚀 Retrieval Strategy Details

### 1. Dense Vector Search (ChromaDB)
- Uses OpenAI embeddings to convert documents into vector space
- Captures **semantic meaning** and conceptual relationships
- Returns top-30 results for fusion
- Great for understanding intent and meaning

### 2. Sparse Keyword Search (BM25)
- Traditional information retrieval algorithm
- Captures **exact keywords and terminology**
- Uses TF-IDF scoring on tokenized documents
- Returns top-30 results for fusion
- Excels at finding specific terms (KYC regulations, document names)

### 3. Reciprocal Rank Fusion (RRF)
- **Formula**: Score = Σ(1 / (K + rank)) for each retriever
- K = 60 (normalization constant)
- Merges dense + sparse results **without redundancy**
- Final results sorted by RRF score (top-90)

### 4. Re-Ranking with FlashRank
- Lightweight neural re-ranker model
- **Model**: ms-marco-MiniLM-L-12-v2 (12M parameters, CPU-friendly)
- Scores the top-90 merged results
- Returns final **top-4 results** with highest relevance
- Adds precision without computational overhead

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run the server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 3. Open the App

- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## 📊 Performance Characteristics

| Metric | Value |
|--------|-------|
| **Query latency** | ~500-800ms (dense + sparse + rerank) |
| **Top-K retrieval** | Top-4 documents after re-ranking |
| **Vector DB** | ChromaDB (persistent) |
| **BM25 index** | In-memory (rebuilt on document upload) |
| **Re-ranker model** | 12M parameters (lightweight) |
| **Memory footprint** | ~2-3GB (embeddings + BM25 + reranker) |

## Features

- Chat with KYC documents using natural language
- Anti-hallucination guardrails (answers only from document context)
- Conversation memory (remembers last 5 exchanges per session)
- Document upload (TXT, PDF, DOCX, MD)
- Source citations with every answer
- Multiple chat sessions
- Beautiful, responsive UI

## Architecture

```
User Query -> FastAPI -> LangChain ConversationalRetrievalChain
                              |
                    Query + Chat History
                              |
                    Standalone Question (condense)
                              |
                    ChromaDB Similarity Search
                              |
                    Top-K Relevant Chunks
                              |
                    GPT-4 with System Prompt + Context
                              |
                    Validated Response -> User
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/chat | Send a chat message |
| POST | /api/v1/documents/upload | Upload a document |
| GET | /api/v1/documents | List all documents |
| POST | /api/v1/sessions/new | Create new session |
| GET | /api/v1/sessions | List all sessions |
| GET | /api/v1/sessions/{id}/history | Get session history |
| DELETE | /api/v1/sessions/{id} | Clear session |
| GET | /health | Health check |

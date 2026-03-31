# KYC Document Chatbot

Production-level RAG-based chatbot for KYC (Know Your Customer) documents.

## Tech Stack

- **Backend**: FastAPI + LangChain + ChromaDB + OpenAI GPT-4
- **Frontend**: React + Tailwind CSS + Vite
- **Embeddings**: OpenAI text-embedding-3-small
- **Vector DB**: ChromaDB (persistent, local)

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

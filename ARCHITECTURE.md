# KYC Chatbot - Hybrid RAG Architecture

## Visual Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE (React/Vercel)                        │
│                          - Chat Input                                        │
│                          - Message History                                  │
│                          - Document Upload                                  │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │   FastAPI Backend (Render)      │
                    │  http://8000/docs               │
                    └────────────────┬────────────────┘
                                     │
                ┌────────────────────┬────────────────────┐
                │                    │                    │
        ┌───────▼────────┐  ┌────────▼──────────┐  ┌──────▼────────┐
        │   Chat Router  │  │ Document Router   │  │  Health Check │
        │  - /chat       │  │  - /upload        │  │  - /health    │
        │  - /history    │  │  - /documents     │  │               │
        │  - /clear      │  │  - /delete        │  │               │
        └───────┬────────┘  └────────┬──────────┘  └───────────────┘
                │                    │
        ┌───────▼──────────────────────┴──────────────┐
        │   RAG SERVICE LAYER                         │
        │ (Integrated Hybrid Retrieval + Re-ranking)  │
        └────┬────────────────────────────────────────┘
             │
    ╔════════╩════════════════════════════════════════════════════════╗
    ║           RETRIEVAL PIPELINE: HYBRID SEARCH                    ║
    ╠════════════════════════════════════════════════════════════════╣
    ║                                                                ║
    ║  ┌─────────────────────────────────────────────────────────┐ ║
    ║  │  1. DENSE VECTOR SEARCH (Semantic)                      │ ║
    ║  │     Component: ChromaDB                                 │ ║
    ║  │     Embeddings: OpenAI text-embedding-3-small           │ ║
    ║  │     Returns: Top-30 chunks by semantic similarity       │ ║
    ║  │     Model: 1536-dimensional vectors                    │ ║
    ║  └─────────────────────────────────────────────────────────┘ ║
    ║                          │                                    ║
    ║                          ▼                                    ║
    ║  ┌─────────────────────────────────────────────────────────┐ ║
    ║  │  2. SPARSE KEYWORD SEARCH (Lexical)                     │ ║
    ║  │     Component: BM25 (Best Matching 25)                 │ ║
    ║  │     Library: rank-bm25 (BM25Okapi)                     │ ║
    ║  │     Tokenization: Regex whitespace + punctuation       │ ║
    ║  │     Returns: Top-30 chunks by TF-IDF score             │ ║
    ║  │     Hits exact keywords, regulations, entities         │ ║
    ║  └─────────────────────────────────────────────────────────┘ ║
    ║                          │                                    ║
    ║                          ▼                                    ║
    ║  ┌─────────────────────────────────────────────────────────┐ ║
    ║  │  3. MERGE: Reciprocal Rank Fusion (RRF)                │ ║
    ║  │     Formula: Score = Σ(1 / (K + rank))                 │ ║
    ║  │     K = 60 (normalization constant)                    │ ║
    ║  │     Combines dense & sparse without duplicates         │ ║
    ║  │     Returns: Top-90 merged documents                   │ ║
    ║  │     Deduplication: by first 200 chars of content       │ ║
    ║  └─────────────────────────────────────────────────────────┘ ║
    ║                          │                                    ║
    ║                          ▼                                    ║
    ║  ┌─────────────────────────────────────────────────────────┐ ║
    ║  │  4. RE-RANKING: FlashRank Neural Re-ranker             │ ║
    ║  │     Model: ms-marco-MiniLM-L-12-v2                    │ ║
    ║  │     Parameters: 12M (lightweight, CPU-only)            │ ║
    ║  │     Input: Query + Top-90 documents                    │ ║
    ║  │     Output: Top-4 re-ranked by relevance              │ ║
    ║  │     Purpose: Precision boost (removes noise)           │ ║
    ║  │     Cache: /tmp/flashrank (model weights)              │ ║
    ║  └─────────────────────────────────────────────────────────┘ ║
    ║                          │                                    ║
    ║                          ▼                                    ║
    ║            Final Context (Top-4 Documents)                   ║
    ║                          │                                    ║
    ╚════════════════════════════╦════════════════════════════════╝
                                 │
                    ┌────────────▼────────────┐
                    │   LLM Processing Layer  │
                    │   OpenAI GPT-4          │
                    │  - Temperature: 0.7     │
                    │  - Max Tokens: 1024     │
                    │  - Top-P: default       │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Answer Generated       │
                    │  + Source Documents    │
                    │  + Chat History        │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Response (JSON)       │
                    │  - answer               │
                    │  - sources              │
                    │  - confidence           │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Frontend Display      │
                    │  - Chat message         │
                    │  - Source references   │
                    └────────────────────────┘
```

## Data Flow: Document Upload

```
     Document Upload
            │
            ▼
    ┌──────────────────┐
    │ File Validation  │ Size check, extension check
    │ (TXT/PDF/DOCX)   │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │ Text Extraction  │
    │ (Format-specific)│
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────────┐
    │ Text Chunking        │ RecursiveCharacterTextSplitter
    │ Chunk Size: 1500     │ Overlap: 200
    │ Separators: \n\n, \n │
    └────────┬─────────────┘
             │
             ▼
    ┌──────────────────────┐
    │ Embedding (Dense)    │ OpenAI Embeddings API
    │ 1536-dim vectors     │
    └────────┬─────────────┘
             │
             ▼
    ┌──────────────────────┐
    │ Store in ChromaDB    │ Persistent vector store
    └────────┬─────────────┘
             │
             ▼
    ┌──────────────────────┐
    │ Rebuild BM25 Index   │ In-memory tokenized index
    │ (All chunks)         │
    └──────────────────────┘
```

## Configuration Parameters

### Text Splitting
```python
CHUNK_SIZE = 1500          # Characters per chunk
CHUNK_OVERLAP = 200        # Overlap between chunks
SEPARATORS = ["\n\n", "\n", ". ", ", ", " ", ""]
```

### Retrieval
```python
TOP_K_RESULTS = 4          # Final top-K after re-ranking
FETCH_K = 12               # Pre-fetch before re-ranking
RRF_K = 60                 # RRF normalization constant
```

### LLM
```python
MODEL_NAME = "gpt-4"
TEMPERATURE = 0.7
MAX_TOKENS = 1024
EMBEDDING_MODEL = "text-embedding-3-small"
```

### FlashRank
```python
MODEL = "ms-marco-MiniLM-L-12-v2"
CACHE_DIR = "/tmp/flashrank"
```

## Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Query Latency | 500-800ms | Dense + Sparse + Rerank |
| ChromaDB Query Time | 50-100ms | 1536-dim vector search |
| BM25 Query Time | 10-50ms | In-memory tokenized search |
| RRF Merge Time | 5-10ms | Deduplication + scoring |
| FlashRank Time | 300-400ms | Neural re-ranking |
| LLM Response Time | 2-5s | GPT-4 generation |
| Memory Usage | 2-3 GB | Embeddings + BM25 + Model |
| Max Documents | 10,000+ | Per collection (indexable) |

## Why This Architecture?

### ✅ Hybrid Retrieval Benefits
1. **Semantic Understanding** (Dense): Captures meaning and intent
2. **Keyword Matching** (Sparse): Finds exact terms and entities
3. **Combined Strength**: RRF merges without over-weighting single method
4. **Robustness**: Works with regulatory, technical, and natural language

### ✅ Re-Ranking Benefits
1. **Precision**: Removes noise from merged results
2. **Lightweight**: 12M parameters, runs on CPU
3. **Efficient**: Only re-ranks top-90, not full collection
4. **Production-Ready**: Battle-tested on MARCO dataset

### ✅ Why Not Just Dense or Sparse?
- **Dense alone**: Misses exact keywords, poor for KYC regulations
- **Sparse alone**: Fails on paraphrasing, synonym matching
- **Hybrid + Re-rank**: Best of both, with precision guarantee

## Deployment URLs

- **Backend API**: https://kyc-chatbot-api.onrender.com
- **Frontend**: https://kyc-bot.vercel.app/
- **API Docs**: https://kyc-chatbot-api.onrender.com/docs
- **Health Check**: https://kyc-chatbot-api.onrender.com/health

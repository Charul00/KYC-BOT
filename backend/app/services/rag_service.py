"""
RAG Service — Dynamic hybrid retrieval pipeline for KYC chatbot.

Architecture:
- Greeting / out-of-scope fast path
- LOOKUP path for exact factual questions
- Hybrid retrieval path for reasoning / analyst-style questions

Goals:
1. Keep greetings instant
2. Make simple factual lookups fast
3. Preserve deeper reasoning for analyst-style questions
4. Reduce latency safely without hurting answer quality too much
"""

import os
import re
import asyncio
import logging
from typing import List, Optional, Tuple, AsyncGenerator

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate

from rank_bm25 import BM25Okapi

from app.config import settings
from app.prompts.templates import (
    QA_PROMPT,
    CONDENSE_QUESTION_PROMPT,
    QUERY_CLASSIFIER_PROMPT,
)

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> List[str]:
    """Simple whitespace + punctuation tokenizer for BM25."""
    return re.findall(r"\w+", text.lower())


# Retrieval config per query type
# top_k = final chunks passed to the LLM after reranking
RETRIEVAL_CONFIG = {
    "GREETING":          {"top_k": 0,  "skip_retrieval": True,  "use_fast_llm": True},
    "OUT_OF_SCOPE":      {"top_k": 0,  "skip_retrieval": True,  "use_fast_llm": True},
    "LOOKUP":            {"top_k": 6,  "skip_retrieval": False, "use_fast_llm": True},
    "SIMPLE":            {"top_k": 8,  "skip_retrieval": False, "use_fast_llm": True},
    "COMPLEX":           {"top_k": 12, "skip_retrieval": False, "use_fast_llm": False},
    "TRICKY":            {"top_k": 12, "skip_retrieval": False, "use_fast_llm": False},
    "ADVERSARIAL":       {"top_k": 8,  "skip_retrieval": False, "use_fast_llm": False},
    # Document-level questions: summarize, parties, clauses, payment terms, governing law, etc.
    "DOCUMENT_ANALYSIS": {"top_k": 16, "skip_retrieval": False, "use_fast_llm": False},
}

GREETING_PATTERNS = re.compile(
    r"^(hi|hello|hey|hii+|good\s*(morning|evening|afternoon)|thanks|thank\s*you|bye|ok|okay|sure|hmm|yo|sup)\s*[!?.]*$",
    re.IGNORECASE,
)


class RAGService:
    """
    Production RAG service with dynamic routing:
    1. Greeting / out-of-scope fast path
    2. LOOKUP path for direct factual questions
    3. Hybrid retrieval path for reasoning-heavy questions
    """

    def __init__(self):
        self._embeddings: Optional[OpenAIEmbeddings] = None
        self._vector_store: Optional[Chroma] = None
        self._llm: Optional[ChatOpenAI] = None
        self._llm_fast: Optional[ChatOpenAI] = None
        self._llm_classifier: Optional[ChatOpenAI] = None
        self._text_splitter: Optional[RecursiveCharacterTextSplitter] = None
        self._qa_chain: Optional[ConversationalRetrievalChain] = None
        self._reranker = None
        self._bm25_index: Optional[BM25Okapi] = None
        self._bm25_docs: List[Document] = []
        self._initialized = False

    # ==========================================
    # Initialization
    # ==========================================

    def initialize(self):
        """Initialize all RAG components."""
        if self._initialized:
            return

        logger.info("Initializing RAG Service...")

        self._embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )

        # Primary splitter — respects paragraph / table / page boundaries
        # Larger chunk size (1500) keeps tables and clauses intact
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=[
                "\n\n\n",           # triple newline (section breaks)
                "\n\n",             # paragraph breaks
                "\n|",              # Markdown table row boundaries
                "\n",               # single newlines
                ". ",               # sentence boundaries
                ", ",
                " ",
                "",
            ],
            is_separator_regex=False,
        )

        self._init_vector_store()
        self._init_reranker()
        self._rebuild_bm25_index()

        # Stronger model for reasoning / analyst-style questions
        self._llm = ChatOpenAI(
            model_name=settings.MODEL_NAME,
            temperature=settings.TEMPERATURE,
            max_tokens=settings.MAX_TOKENS,
            openai_api_key=settings.OPENAI_API_KEY,
            streaming=True,
        )

        # Fast model for greetings / lookups / simple factual answers
        self._llm_fast = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=settings.TEMPERATURE,
            max_tokens=settings.MAX_TOKENS,
            openai_api_key=settings.OPENAI_API_KEY,
            streaming=True,
        )

        # Classifier model
        self._llm_classifier = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0.0,
            max_tokens=15,
            openai_api_key=settings.OPENAI_API_KEY,
        )

        self._build_qa_chain()

        self._initialized = True
        logger.info("RAG Service initialized (dynamic routing enabled).")

    def _init_vector_store(self):
        """Initialize ChromaDB."""
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        persist_dir = settings.CHROMA_PERSIST_DIR

        if os.path.exists(persist_dir) and os.listdir(persist_dir):
            logger.info(f"Loading existing ChromaDB from {persist_dir}")
            self._vector_store = Chroma(
                persist_directory=persist_dir,
                embedding_function=self._embeddings,
                collection_name="kyc_documents",
            )
            count = self._vector_store._collection.count()
            logger.info(f"Loaded {count} existing document chunks.")
        else:
            logger.info("Creating new ChromaDB vector store...")
            os.makedirs(persist_dir, exist_ok=True)
            self._vector_store = Chroma(
                persist_directory=persist_dir,
                embedding_function=self._embeddings,
                collection_name="kyc_documents",
            )
            self._load_default_documents()

    def _init_reranker(self):
        """Initialize FlashRank re-ranker."""
        try:
            from flashrank import Ranker
            cache_dir = os.environ.get("FLASHRANK_CACHE_DIR", "/tmp/flashrank")
            os.makedirs(cache_dir, exist_ok=True)
            self._reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir=cache_dir)
            logger.info("FlashRank re-ranker loaded: ms-marco-MiniLM-L-12-v2")
        except Exception as e:
            logger.warning(f"FlashRank not available, falling back to basic ranking: {e}")
            self._reranker = None

    def _rebuild_bm25_index(self):
        """Rebuild BM25 index from all chunks in ChromaDB."""
        try:
            collection = self._vector_store._collection
            all_data = collection.get(include=["documents", "metadatas"])

            if all_data["documents"]:
                self._bm25_docs = [
                    Document(page_content=doc, metadata=meta or {})
                    for doc, meta in zip(
                        all_data["documents"],
                        all_data["metadatas"] or [{}] * len(all_data["documents"]),
                    )
                ]
                tokenized = [_tokenize(doc.page_content) for doc in self._bm25_docs]
                self._bm25_index = BM25Okapi(tokenized)
                logger.info(f"BM25 index built with {len(self._bm25_docs)} documents.")
            else:
                self._bm25_index = None
                self._bm25_docs = []
        except Exception as e:
            logger.warning(f"BM25 index build failed: {e}")
            self._bm25_index = None

    def _load_default_documents(self):
        """Load documents from the default directory on cold start."""
        from pathlib import Path

        docs_dir = Path(settings.DOCUMENTS_DIR)
        if not docs_dir.exists():
            logger.warning(f"Documents directory not found: {docs_dir}")
            return

        documents = []
        for file_path in docs_dir.iterdir():
            if file_path.suffix in [".txt", ".md"]:
                logger.info(f"Loading: {file_path.name}")
                content = file_path.read_text(encoding="utf-8")
                documents.append(
                    Document(
                        page_content=content,
                        metadata={"source": file_path.name, "file_type": file_path.suffix},
                    )
                )
            elif file_path.suffix == ".pdf":
                logger.info(f"Loading PDF: {file_path.name}")
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(str(file_path))
                    text = "\n".join(p.extract_text() or "" for p in reader.pages)
                    documents.append(
                        Document(
                            page_content=text,
                            metadata={"source": file_path.name, "file_type": ".pdf"},
                        )
                    )
                except Exception as e:
                    logger.error(f"Error loading PDF {file_path.name}: {e}")

        if documents:
            self.add_documents(documents)

    # ==========================================
    # Document Processing
    # ==========================================

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks using Recursive Character Text Splitting.
        Preserves page_number, has_tables, document_title metadata across child chunks
        so every chunk can be cited accurately.
        """
        chunks = self._text_splitter.split_documents(documents)
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            # Forward page-level metadata from parent document if not already set
            if "page_number" not in chunk.metadata:
                # Try to infer from content header "[Page N of M — ...]"
                import re
                m = re.search(r"\[Page (\d+) of (\d+)", chunk.page_content)
                if m:
                    chunk.metadata["page_number"] = int(m.group(1))
                    chunk.metadata["total_pages"] = int(m.group(2))
            # Mark table chunks explicitly
            if "| --- |" in chunk.page_content or "| --- " in chunk.page_content:
                chunk.metadata["has_table_content"] = True
        logger.info(f"Chunked {len(documents)} docs into {len(chunks)} chunks.")
        return chunks

    def add_documents(self, documents: List[Document]) -> int:
        """Add documents: chunk -> embed -> store in ChromaDB + rebuild BM25."""
        chunks = self.chunk_documents(documents)
        if chunks:
            self._vector_store.add_documents(chunks)
            self._rebuild_bm25_index()
            logger.info(f"Added {len(chunks)} chunks. BM25 index refreshed.")
        return len(chunks)

    # ==========================================
    # Query Intelligence Helpers
    # ==========================================

    def _is_case_or_customer_query(self, query: str) -> bool:
        """
        Detect broader case-analysis questions.
        """
        query_lower = query.lower()
        keywords = [
            "customer", "case", "profile", "risk", "alert",
            "adverse media", "source of wealth", "mule", "transaction",
            "transactions", "review", "high risk", "low risk", "anomaly",
            "manual review", "flag", "flagged", "suspicious",
            "explain the case", "summarize the case", "should this be flagged",
            "what checks", "next steps", "monitoring", "pkyc", "perpetual kyc"
        ]
        return any(keyword in query_lower for keyword in keywords)
    
    def _is_process_document_query(self, query: str) -> bool:
        q = query.lower().strip()
        keywords = [
            "prioritization", "priority", "escalation", "escalated",
            "review rules", "main review rules", "process document",
            "process rules", "monitoring", "manual review",
            "ongoing monitoring", "brd", "business requirements",
            "uploaded process document",
        ]
        return any(k in q for k in keywords)

    def _is_financial_analytical_query(self, query: str) -> bool:
        """
        Detect questions about financial data, annual reports, tables, graphs, charts.
        These need DOCUMENT_ANALYSIS routing (top_k=16, strong LLM, big context).
        """
        q = query.lower()
        keywords = [
            # Financial metrics
            "revenue", "net revenue", "total revenue",
            "profit", "net profit", "gross profit", "operating profit",
            "earnings", "eps", "earnings per share",
            "ebitda", "ebit", "operating income", "net income",
            "cash flow", "free cash flow", "operating cash flow",
            "balance sheet", "income statement", "financial statement",
            "assets", "total assets", "liabilities", "equity", "shareholders equity",
            "market cap", "market capitalization",
            "dividends", "dividend per share",
            "return on equity", "roe", "return on assets", "roa",
            "margin", "gross margin", "operating margin", "net margin",
            "debt", "long-term debt", "short-term debt", "leverage",
            "quarterly", "annual", "fiscal year", "fy20", "fy21", "fy22", "fy23", "fy24",
            "q1", "q2", "q3", "q4",
            # Report sections
            "annual report", "10-k", "10k", "20-f", "proxy statement",
            "risk factor", "risk factors",
            "segment", "business segment", "revenue by segment",
            "geographic", "revenue by region",
            "headcount", "employees", "workforce",
            # Visual content
            "chart", "graph", "figure", "table", "exhibit",
            "bar chart", "line graph", "pie chart",
            "what does the chart", "what does the graph", "what does the table",
            # Comparative
            "year over year", "yoy", "compared to", "versus", "vs",
            "increased", "decreased", "grew", "declined", "trend",
            "highlight", "key financial", "financial highlight",
            # Specific companies / report types
            "goldman sachs", "annual results", "10-k filing",
        ]
        return any(k in q for k in keywords)

    def _is_document_analysis_query(self, query: str) -> bool:
        """
        Detect questions about an uploaded document as a whole —
        agreements, forms, AOFs, contracts, policies, clauses, parties, etc.
        These need DOCUMENT_ANALYSIS routing (top_k=16, strong LLM).
        """
        q = query.lower()
        keywords = [
            # Summary / overview
            "summarize", "summary", "what is this document", "what is the document",
            "explain this document", "explain this agreement", "what does this document",
            "what is this about", "what is the document about", "tell me about this document",
            "overview of this", "in simple terms",
            # Parties / signatories
            "parties involved", "who are the parties", "party to this", "signatory",
            "signatories", "both parties", "first party", "second party",
            "who signed", "who are the signers",
            # Legal clauses
            "notice period", "governing law", "jurisdiction", "applicable law",
            "termination clause", "termination condition", "termination",
            "confidentiality clause", "confidentiality", "non-disclosure",
            "renewal clause", "automatic renewal", "auto renewal",
            "arbitration", "dispute resolution", "force majeure",
            # Agreement details
            "agreement date", "start date", "end date", "effective date",
            "validity period", "expiry date", "commencement date",
            "duration of this", "term of this",
            # Obligations / responsibilities
            "my responsibilities", "my obligations", "your responsibilities",
            "obligations of", "responsibilities of", "other party",
            "deliverables", "scope of work", "services provided",
            # Payment
            "payment terms", "payment amount", "payment schedule",
            "fee structure", "charges mentioned",
            # Risk / signing advice
            "risky clause", "unfavorable clause", "one-sided", "should i sign",
            "what should i check", "key risks", "important clauses",
            "pay attention to", "before signing",
            # Breach / penalties
            "penalty", "penalties", "breach condition", "breach of contract",
            "what happens if i break",
            # Execution / signatures
            "is it signed", "fully executed", "signature section", "stamp and seal",
            "on what date was", "agreement signed", "signed on",
        ]
        return any(k in q for k in keywords)

    def _is_lookup_query(self, query: str) -> bool:
        """
        Detect exact factual lookup questions.
        These should avoid rewrite and rerank.
        """
        q = query.strip().lower()

        if "cust-" in q:
            if q.startswith("who is") or q.startswith("what is") or q.startswith("show"):
                return True

        lookup_patterns = [
            r"^who is\s+cust-\d+\??$",
            r"^who is\s+customer\s+cust-\d+\??$",
            r"^what is\s+onboarding duration\??$",
            r"^what is\s+the onboarding duration\??$",
            r"^what is\s+occupation\??$",
            r"^what is\s+the occupation\??$",
            r"^what is\s+name\??$",
            r"^what is\s+the name\??$",
            r"^what is\s+profile type\??$",
            r"^what is\s+the profile type\??$",
            r"^what is\s+location\??$",
            r"^what is\s+the location\??$",
            r"^what is\s+onboarding channel\??$",
            r"^what is\s+the onboarding channel\??$",
        ]

        return any(re.match(pattern, q) for pattern in lookup_patterns)

    def _select_answer_llm(self, query: str, config: dict, query_type: str):
        """
        Use fast model for greetings and lookups.
        Use stronger model for document analysis, case questions, and complex reasoning.
        """
        if query_type in {"GREETING", "OUT_OF_SCOPE", "LOOKUP"}:
            return self._llm_fast

        if query_type in {"DOCUMENT_ANALYSIS", "COMPLEX", "TRICKY", "ADVERSARIAL"}:
            return self._llm

        if query_type == "SIMPLE" and not self._is_case_or_customer_query(query):
            return self._llm_fast

        return self._llm

    def _resolve_query_type(self, classified_type: str, query: str) -> str:
        """
        Override classifier with deterministic pattern matching.
        Order matters: most specific checks first.
        """
        if self._is_lookup_query(query):
            return "LOOKUP"

        # Financial / analytical report queries → maximum context + strong LLM
        if self._is_financial_analytical_query(query):
            return "DOCUMENT_ANALYSIS"

        # Agreement / form / document-level analysis → maximum context
        if self._is_document_analysis_query(query):
            return "DOCUMENT_ANALYSIS"

        if self._is_process_document_query(query):
            return "COMPLEX"

        return classified_type

    # ==========================================
    # Query Classification & Rewriting
    # ==========================================

    def _classify_query(self, query: str) -> str:
        """Sync classify — used by legacy get_answer path."""
        if GREETING_PATTERNS.match(query.strip()):
            return "GREETING"
        try:
            prompt = QUERY_CLASSIFIER_PROMPT.format(question=query)
            response = self._llm_classifier.invoke(prompt)
            category = response.content.strip().upper().replace(" ", "_")
            category = category if category in RETRIEVAL_CONFIG else "SIMPLE"

            # Never block document-level questions as out-of-scope when docs are loaded
            if category == "OUT_OF_SCOPE" and self.get_document_count() > 0:
                category = "SIMPLE"

            resolved = self._resolve_query_type(category, query)
            logger.info(f"Query classified as: {resolved}")
            return resolved
        except Exception as e:
            logger.warning(f"Classification failed, defaulting to SIMPLE: {e}")
            return self._resolve_query_type("SIMPLE", query)

    async def _classify_query_async(self, query: str) -> str:
        """Async classify — used by streaming path."""
        if GREETING_PATTERNS.match(query.strip()):
            return "GREETING"
        try:
            prompt = QUERY_CLASSIFIER_PROMPT.format(question=query)
            response = await self._llm_classifier.ainvoke(prompt)
            category = response.content.strip().upper().replace(" ", "_")
            category = category if category in RETRIEVAL_CONFIG else "SIMPLE"

            # Never block document-level questions as out-of-scope when docs are loaded
            if category == "OUT_OF_SCOPE" and self.get_document_count() > 0:
                category = "SIMPLE"

            resolved = self._resolve_query_type(category, query)
            logger.info(f"Query classified as: {resolved}")
            return resolved
        except Exception as e:
            logger.warning(f"Async classification failed, defaulting to SIMPLE: {e}")
            return self._resolve_query_type("SIMPLE", query)

    def _rewrite_query(self, query: str, chat_history: List[Tuple[str, str]]) -> str:
        """
        Sync rewrite — skip rewrite for exact lookup queries.
        """
        if self._is_lookup_query(query):
            return query

        if not chat_history:
            return query

        follow_up_markers = [
            "it", "that", "this", "those", "these", "they", "them",
            "same", "above", "previous", "also", "what about", "and the",
            "how about", "is there", "what's"
        ]
        query_lower = query.lower()
        needs_rewrite = any(marker in query_lower for marker in follow_up_markers)

        if not needs_rewrite and len(query.split()) > 5:
            return query

        try:
            history_str = ""
            for human, ai in chat_history[-3:]:
                history_str += f"Human: {human}\nAI: {ai[:200]}\n\n"

            prompt = CONDENSE_QUESTION_PROMPT.format(
                chat_history=history_str,
                question=query
            )
            response = self._llm_fast.invoke(prompt)
            rewritten = response.content.strip()

            if rewritten and len(rewritten) > 3:
                logger.info(f"Query rewritten: '{query}' → '{rewritten}'")
                return rewritten
            return query
        except Exception as e:
            logger.warning(f"Query rewriting failed: {e}")
            return query

    async def _rewrite_query_async(self, query: str, chat_history: List[Tuple[str, str]]) -> str:
        """Async rewrite — skip rewrite for exact lookup queries."""
        if self._is_lookup_query(query):
            return query

        if not chat_history:
            return query

        follow_up_markers = [
            "it", "that", "this", "those", "these", "they", "them",
            "same", "above", "previous", "also", "what about", "and the",
            "how about", "is there", "what's"
        ]
        query_lower = query.lower()
        needs_rewrite = any(marker in query_lower for marker in follow_up_markers)

        if not needs_rewrite and len(query.split()) > 5:
            return query

        try:
            history_str = ""
            for human, ai in chat_history[-3:]:
                history_str += f"Human: {human}\nAI: {ai[:200]}\n\n"

            prompt = CONDENSE_QUESTION_PROMPT.format(
                chat_history=history_str,
                question=query
            )
            response = await self._llm_fast.ainvoke(prompt)
            rewritten = response.content.strip()

            if rewritten and len(rewritten) > 3:
                logger.info(f"Query rewritten: '{query}' → '{rewritten}'")
                return rewritten
            return query
        except Exception as e:
            logger.warning(f"Async query rewriting failed: {e}")
            return query

    # ==========================================
    # Retrieval
    # ==========================================

    def _bm25_search(self, query: str, k: int = 10) -> List[Tuple[Document, float]]:
        """BM25 sparse keyword search (sync — runs in memory)."""
        if not self._bm25_index or not self._bm25_docs:
            return []

        tokens = _tokenize(query)
        scores = self._bm25_index.get_scores(tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [(self._bm25_docs[i], float(scores[i])) for i in top_indices if scores[i] > 0]

    def _rerank(self, query: str, docs: List[Document], top_k: int = 4) -> List[Document]:
        """Re-rank documents using FlashRank for precision."""
        if not self._reranker or not docs:
            return docs[:top_k]

        try:
            from flashrank import RerankRequest

            passages = [{"id": i, "text": doc.page_content, "meta": doc.metadata} for i, doc in enumerate(docs)]
            request = RerankRequest(query=query, passages=passages)
            results = self._reranker.rerank(request)

            reranked = []
            for r in results[:top_k]:
                idx = r["id"]
                if idx < len(docs):
                    reranked.append(docs[idx])

            logger.info(f"Re-ranked {len(docs)} -> top {len(reranked)}")
            return reranked if reranked else docs[:top_k]
        except Exception as e:
            logger.warning(f"Re-ranking failed, using original order: {e}")
            return docs[:top_k]

    def _rrf_merge(self, dense_results: List[Document], bm25_docs: List[Document], fetch_k: int) -> List[Document]:
        """Reciprocal Rank Fusion — merges dense + sparse results."""
        RRF_K = 60
        doc_map = {}
        rrf_scores = {}

        for rank, doc in enumerate(dense_results):
            key = doc.page_content[:200]
            doc_map[key] = doc
            rrf_scores[key] = rrf_scores.get(key, 0) + 1.0 / (RRF_K + rank + 1)

        for rank, doc in enumerate(bm25_docs):
            key = doc.page_content[:200]
            if key not in doc_map:
                doc_map[key] = doc
            rrf_scores[key] = rrf_scores.get(key, 0) + 1.0 / (RRF_K + rank + 1)

        sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        return [doc_map[key] for key in sorted_keys if key in doc_map][:fetch_k]

    def _lookup_search(self, query: str, k: int = 6) -> List[Document]:
        """
        Lightweight retrieval for factual questions.
        Uses modest fetch window with BM25 merge.
        """
        fetch_k = max(k + 4, 10)
        dense_results = self._vector_store.similarity_search(query, k=fetch_k)
        bm25_results = self._bm25_search(query, k=fetch_k)
        bm25_docs = [doc for doc, _ in bm25_results]

        if bm25_docs:
            merged = self._rrf_merge(dense_results, bm25_docs, fetch_k=fetch_k)
            logger.info(f"Lookup: {len(dense_results)} dense + {len(bm25_docs)} BM25 -> {len(merged[:k])} final")
            return merged[:k]

        logger.info(f"Lookup: {len(dense_results)} dense only -> {len(dense_results[:k])} final")
        return dense_results[:k]

    async def _lookup_search_async(self, query: str, k: int = 6) -> List[Document]:
        """
        Async factual retrieval with modest fetch window and BM25 merge.
        """
        fetch_k = max(k + 4, 10)
        dense_task = self._vector_store.asimilarity_search(query, k=fetch_k)
        bm25_results = self._bm25_search(query, k=fetch_k)
        dense_results = await dense_task
        bm25_docs = [doc for doc, _ in bm25_results]

        if bm25_docs:
            merged = self._rrf_merge(dense_results, bm25_docs, fetch_k=fetch_k)
            logger.info(f"Async lookup: {len(dense_results)} dense + {len(bm25_docs)} BM25 -> {len(merged[:k])} final")
            return merged[:k]

        logger.info(f"Async lookup: {len(dense_results)} dense only -> {len(dense_results[:k])} final")
        return dense_results[:k]

    def hybrid_search(self, query: str, k: int = None) -> List[Document]:
        """Sync hybrid retrieval for reasoning-heavy questions."""
        k = k or settings.TOP_K_RESULTS
        # Generous fetch window — gather wide candidates, reranker picks the best
        fetch_k = max(k * 2 + 5, 20)
        dense_results = self._vector_store.similarity_search(query, k=fetch_k)
        bm25_results = self._bm25_search(query, k=fetch_k)
        bm25_docs = [doc for doc, _ in bm25_results]
        merged = self._rrf_merge(dense_results, bm25_docs, fetch_k)

        # Let FlashRank see all merged candidates — no artificial cap
        final = self._rerank(query, merged, top_k=k)
        logger.info(f"Hybrid: {len(dense_results)} dense + {len(bm25_docs)} BM25 -> {len(merged)} merged -> {len(final)} final (k={k})")
        return final

    async def _hybrid_search_async(self, query: str, k: int) -> List[Document]:
        """Async hybrid retrieval for reasoning-heavy questions."""
        # Generous fetch window — gather wide candidates, reranker picks the best
        fetch_k = max(k * 2 + 5, 20)

        dense_task = self._vector_store.asimilarity_search(query, k=fetch_k)
        bm25_results = self._bm25_search(query, k=fetch_k)
        dense_results = await dense_task

        bm25_docs = [doc for doc, _ in bm25_results]
        merged = self._rrf_merge(dense_results, bm25_docs, fetch_k)

        # Let FlashRank see all merged candidates — no artificial cap
        final = self._rerank(query, merged, top_k=k)

        logger.info(f"Async hybrid: {len(dense_results)} dense + {len(bm25_docs)} BM25 -> {len(merged)} merged -> {len(final)} final (k={k})")
        return final

    # ==========================================
    # QA Chain
    # ==========================================

    def _build_qa_chain(self):
        """Build ConversationalRetrievalChain as fallback for non-streaming path."""
        qa_prompt = PromptTemplate(
            template=QA_PROMPT,
            input_variables=["context", "chat_history", "question"],
        )
        condense_prompt = PromptTemplate(
            template=CONDENSE_QUESTION_PROMPT,
            input_variables=["chat_history", "question"],
        )

        retriever = self._vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": settings.TOP_K_RESULTS},
        )

        self._qa_chain = ConversationalRetrievalChain.from_llm(
            llm=self._llm,
            retriever=retriever,
            condense_question_prompt=condense_prompt,
            combine_docs_chain_kwargs={"prompt": qa_prompt},
            return_source_documents=True,
            verbose=False,
        )
        logger.info("QA Chain built.")

    # ==========================================
    # Prompt Helpers
    # ==========================================

    def _build_prompt(self, context: str, chat_history: str, question: str) -> str:
        prompt = PromptTemplate(
            template=QA_PROMPT,
            input_variables=["context", "chat_history", "question"],
        )
        return prompt.format(
            context=context,
            chat_history=chat_history,
            question=question,
        )

    def _format_history(self, chat_history: List[Tuple[str, str]]) -> str:
        history_str = ""
        for human, ai in chat_history[-settings.MAX_MEMORY_MESSAGES:]:
            history_str += f"Human: {human}\nAssistant: {ai}\n\n"
        return history_str

    def _build_sources_data(self, relevant_docs: List[Document]) -> List[dict]:
        seen = set()
        sources = []
        for doc in relevant_docs:
            key = doc.page_content[:150]
            if key in seen:
                continue
            seen.add(key)
            meta = doc.metadata.copy()
            # Add a human-readable citation label
            source_name = meta.get("source", "Document")
            page_num = meta.get("page_number")
            if page_num:
                meta["citation"] = f"{source_name} — Page {page_num}"
            else:
                meta["citation"] = source_name
            sources.append({
                "content": doc.page_content[:400] + ("..." if len(doc.page_content) > 400 else ""),
                "metadata": meta,
            })
        return sources

    # ==========================================
    # Streaming Answer Pipeline
    # ==========================================

    async def stream_answer(
        self,
        query: str,
        chat_history: List[Tuple[str, str]],
    ) -> AsyncGenerator[dict, None]:
        """
        Streaming pipeline — yields token dicts then a final summary dict.
        """
        if not self._initialized:
            self.initialize()

        try:
            # Step 1: classify first
            query_type = await self._classify_query_async(query)
            config = RETRIEVAL_CONFIG.get(query_type, RETRIEVAL_CONFIG["SIMPLE"])

            # Step 2: rewrite only when needed
            if query_type == "LOOKUP":
                search_query = query
            else:
                search_query = await self._rewrite_query_async(query, chat_history)

            logger.info(
                f"Stream pipeline: type={query_type}, top_k={config['top_k']}, "
                f"fast_llm={config['use_fast_llm']}, "
                f"case_query={self._is_case_or_customer_query(query)}, "
                f"lookup_query={self._is_lookup_query(query)}"
            )

            answer_llm = self._select_answer_llm(query, config, query_type)

            # Greetings / out-of-scope fast path
            if config["skip_retrieval"]:
                if query_type == "GREETING":
                    prompt_text = (
                        f"You are the eClerx KYC Assistant. The user said: \"{query}\". "
                        f"Respond warmly and naturally, then offer to help with KYC documents. "
                        f"Keep it to 1–2 sentences."
                    )
                else:
                    prompt_text = (
                        f"You are the eClerx KYC Assistant. The user asked: \"{query}\". "
                        f"This is outside your scope. Politely say you're designed for KYC "
                        f"document queries only. Keep it friendly and brief."
                    )

                async for chunk in answer_llm.astream(prompt_text):
                    if chunk.content:
                        yield {"token": chunk.content, "done": False}

                yield {"done": True, "sources": [], "query_type": query_type}
                return

            # Step 3: retrieval
            if query_type == "LOOKUP":
                relevant_docs = await self._lookup_search_async(search_query, k=config["top_k"])
            else:
                relevant_docs = await self._hybrid_search_async(search_query, k=config["top_k"])

            # Step 4: build context
            context = "\n\n---\n\n".join(doc.page_content for doc in relevant_docs)
            if not context.strip():
                context = "[No relevant document sections were found for this query.]"

            # Step 5: format history and prompt
            history_str = self._format_history(chat_history)
            formatted = self._build_prompt(context=context, chat_history=history_str, question=query)

            # Step 6: answer stream
            async for chunk in answer_llm.astream(formatted):
                if chunk.content:
                    yield {"token": chunk.content, "done": False}

            # Step 7: final metadata
            yield {
                "done": True,
                "sources": self._build_sources_data(relevant_docs),
                "query_type": query_type,
            }

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield {"token": "I encountered an error while processing your question. Please try again.", "done": False}
            yield {"done": True, "sources": [], "query_type": "SIMPLE"}

    # ==========================================
    # Non-Streaming Answer Pipeline
    # ==========================================

    async def get_answer(self, query: str, chat_history: List[Tuple[str, str]]) -> dict:
        """
        Non-streaming pipeline — gathers full answer then returns.
        Used by /chat endpoint.
        """
        if not self._initialized:
            self.initialize()

        try:
            query_type = self._classify_query(query)
            config = RETRIEVAL_CONFIG.get(query_type, RETRIEVAL_CONFIG["SIMPLE"])

            if query_type == "LOOKUP":
                search_query = query
            else:
                search_query = self._rewrite_query(query, chat_history)

            logger.info(
                f"Pipeline: type={query_type}, top_k={config['top_k']}, "
                f"fast_llm={config['use_fast_llm']}, "
                f"case_query={self._is_case_or_customer_query(query)}, "
                f"lookup_query={self._is_lookup_query(query)}"
            )

            answer_llm = self._select_answer_llm(query, config, query_type)

            if config["skip_retrieval"]:
                if query_type == "GREETING":
                    prompt_text = (
                        f"You are the eClerx KYC Assistant. The user said: \"{query}\". "
                        f"Respond warmly and naturally, then offer to help with KYC documents. "
                        f"Keep it to 1–2 sentences."
                    )
                else:
                    prompt_text = (
                        f"You are the eClerx KYC Assistant. The user asked: \"{query}\". "
                        f"This is outside your scope. Politely say you're designed for KYC "
                        f"document queries only. Keep it friendly and brief."
                    )

                response = await answer_llm.ainvoke(prompt_text)
                return {
                    "answer": response.content,
                    "source_documents": [],
                    "query_type": query_type,
                }

            if query_type == "LOOKUP":
                relevant_docs = await self._lookup_search_async(search_query, k=config["top_k"])
            else:
                relevant_docs = await self._hybrid_search_async(search_query, k=config["top_k"])

            context = "\n\n---\n\n".join(doc.page_content for doc in relevant_docs)
            if not context.strip():
                context = "[No relevant document sections were found for this query.]"

            history_str = self._format_history(chat_history)
            formatted = self._build_prompt(context=context, chat_history=history_str, question=query)

            response = await answer_llm.ainvoke(formatted)

            logger.info(f"Answer generated: {len(response.content)} chars, {len(relevant_docs)} sources")
            return {
                "answer": response.content,
                "source_documents": relevant_docs,
                "query_type": query_type,
            }

        except Exception as e:
            logger.error(f"Error getting answer: {e}")
            raise

    # ==========================================
    # Utility
    # ==========================================

    def get_document_count(self) -> int:
        if self._vector_store:
            return self._vector_store._collection.count()
        return 0

    def is_ready(self) -> bool:
        return self._initialized and self._vector_store is not None

    def reset_vector_store(self):
        if self._vector_store:
            self._vector_store.delete_collection()
            self._init_vector_store()
            self._rebuild_bm25_index()

    def remove_documents_by_source(self, filename: str) -> int:
        """
        Delete every chunk whose metadata["source"] == filename from ChromaDB,
        then rebuild the BM25 index to stay in sync.
        Returns the number of chunks deleted.
        """
        if not self._vector_store:
            return 0
        try:
            collection = self._vector_store._collection

            # Find IDs for this source
            result = collection.get(
                where={"source": filename},
                include=[],   # only need IDs
            )
            ids = result.get("ids", [])
            if not ids:
                logger.info(f"No chunks found for source '{filename}' — nothing to delete.")
                return 0

            collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} chunks for source '{filename}' from ChromaDB.")

            # Rebuild BM25 so it stays in sync with ChromaDB
            self._rebuild_bm25_index()

            return len(ids)
        except Exception as e:
            logger.error(f"Failed to remove documents for '{filename}': {e}")
            return 0


# Singleton
rag_service = RAGService()
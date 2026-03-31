"""
RAG Service — Production-level hybrid retrieval pipeline.
Architecture: Query Classification → Query Rewriting → ChromaDB (dense) + BM25 (sparse) → RRF → Re-Rank → LLM.
"""

import os
import re
import logging
from typing import List, Optional, Tuple
from pathlib import Path

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


# ── Retrieval config per query type
RETRIEVAL_CONFIG = {
    "GREETING":      {"top_k": 0,  "skip_retrieval": True},
    "OUT_OF_SCOPE":  {"top_k": 0,  "skip_retrieval": True},
    "SIMPLE":        {"top_k": 4,  "skip_retrieval": False},
    "COMPLEX":       {"top_k": 8,  "skip_retrieval": False},
    "TRICKY":        {"top_k": 8,  "skip_retrieval": False},
    "ADVERSARIAL":   {"top_k": 6,  "skip_retrieval": False},
}

# ── Greeting patterns (fast path — no LLM call needed)
GREETING_PATTERNS = re.compile(
    r"^(hi|hello|hey|hii+|good\s*(morning|evening|afternoon)|thanks|thank\s*you|bye|ok|okay|sure|hmm|yo|sup)\s*[!?.]*$",
    re.IGNORECASE,
)


class RAGService:
    """
    Production RAG service with:
    1. Query classification (greeting / simple / complex / tricky / adversarial / out-of-scope)
    2. Query rewriting (follow-up → standalone question)
    3. Hybrid retrieval: ChromaDB (dense) + BM25 (sparse)
    4. Reciprocal Rank Fusion
    5. FlashRank re-ranking
    6. Adaptive context window per query type
    """

    def __init__(self):
        self._embeddings: Optional[OpenAIEmbeddings] = None
        self._vector_store: Optional[Chroma] = None
        self._llm: Optional[ChatOpenAI] = None
        self._llm_fast: Optional[ChatOpenAI] = None  # lightweight model for classification
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

        # 1. Embeddings
        self._embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )

        # 2. Text splitter
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", ", ", " ", ""],
            is_separator_regex=False,
        )

        # 3. ChromaDB vector store
        self._init_vector_store()

        # 4. FlashRank re-ranker (lightweight, no GPU needed)
        self._init_reranker()

        # 5. BM25 index
        self._rebuild_bm25_index()

        # 6. Main LLM (for answering)
        self._llm = ChatOpenAI(
            model_name=settings.MODEL_NAME,
            temperature=settings.TEMPERATURE,
            max_tokens=settings.MAX_TOKENS,
            openai_api_key=settings.OPENAI_API_KEY,
        )

        # 7. Fast LLM (for classification + query rewriting — cheaper calls)
        self._llm_fast = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0.0,
            max_tokens=100,
            openai_api_key=settings.OPENAI_API_KEY,
        )

        # 8. QA chain (fallback)
        self._build_qa_chain()

        self._initialized = True
        logger.info("RAG Service initialized (ChromaDB + BM25 + FlashRank + Query Classifier).")

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
        """Initialize FlashRank re-ranker (lightweight, CPU-only)."""
        try:
            from flashrank import Ranker
            self._reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp/flashrank")
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
        """Load documents from the default directory."""
        docs_dir = Path(settings.DOCUMENTS_DIR)
        if not docs_dir.exists():
            logger.warning(f"Documents directory not found: {docs_dir}")
            return

        documents = []
        for file_path in docs_dir.iterdir():
            if file_path.suffix in [".txt", ".md"]:
                logger.info(f"Loading: {file_path.name}")
                content = file_path.read_text(encoding="utf-8")
                documents.append(Document(
                    page_content=content,
                    metadata={"source": file_path.name, "file_type": file_path.suffix},
                ))
            elif file_path.suffix == ".pdf":
                logger.info(f"Loading PDF: {file_path.name}")
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(str(file_path))
                    text = "\n".join(p.extract_text() or "" for p in reader.pages)
                    documents.append(Document(
                        page_content=text,
                        metadata={"source": file_path.name, "file_type": ".pdf"},
                    ))
                except Exception as e:
                    logger.error(f"Error loading PDF {file_path.name}: {e}")

        if documents:
            self.add_documents(documents)

    # ==========================================
    # Document Processing
    # ==========================================

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks using Recursive Character Text Splitting."""
        chunks = self._text_splitter.split_documents(documents)
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
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
    # Query Classification & Rewriting
    # ==========================================

    def _classify_query(self, query: str) -> str:
        """Classify the query type using fast LLM or regex."""
        # Fast path — check greeting regex
        if GREETING_PATTERNS.match(query.strip()):
            return "GREETING"

        try:
            prompt = QUERY_CLASSIFIER_PROMPT.format(question=query)
            response = self._llm_fast.invoke(prompt)
            category = response.content.strip().upper().replace(" ", "_")
            if category in RETRIEVAL_CONFIG:
                logger.info(f"Query classified as: {category}")
                return category
            logger.warning(f"Unknown category '{category}', defaulting to SIMPLE")
            return "SIMPLE"
        except Exception as e:
            logger.warning(f"Classification failed, defaulting to SIMPLE: {e}")
            return "SIMPLE"

    def _rewrite_query(self, query: str, chat_history: List[Tuple[str, str]]) -> str:
        """Rewrite follow-up questions into standalone queries using chat history."""
        if not chat_history:
            return query

        # If the query is already self-contained (no pronouns/references), skip rewriting
        follow_up_markers = ["it", "that", "this", "those", "these", "they", "them",
                             "same", "above", "previous", "also", "what about", "and the",
                             "how about", "is there", "what's"]
        query_lower = query.lower()
        needs_rewrite = any(marker in query_lower for marker in follow_up_markers)

        if not needs_rewrite and len(query.split()) > 5:
            return query

        try:
            history_str = ""
            for human, ai in chat_history[-3:]:  # Last 3 exchanges for context
                history_str += f"Human: {human}\nAI: {ai[:200]}\n\n"

            prompt = CONDENSE_QUESTION_PROMPT.format(
                chat_history=history_str,
                question=query,
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

    # ==========================================
    # Hybrid Retrieval: Dense + BM25 + Re-Rank
    # ==========================================

    def _bm25_search(self, query: str, k: int = 10) -> List[Tuple[Document, float]]:
        """BM25 sparse keyword search."""
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

            passages = [
                {"id": i, "text": doc.page_content, "meta": doc.metadata}
                for i, doc in enumerate(docs)
            ]
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

    def hybrid_search(self, query: str, k: int = None) -> List[Document]:
        """
        Hybrid retrieval pipeline:
        1. ChromaDB dense vector search (semantic)
        2. BM25 sparse keyword search (lexical)
        3. Reciprocal Rank Fusion to merge
        4. FlashRank re-rank for final precision
        """
        k = k or settings.TOP_K_RESULTS
        fetch_k = k * 3  # Over-fetch then re-rank

        # Dense search
        dense_results = self._vector_store.similarity_search(query, k=fetch_k)

        # BM25 search
        bm25_results = self._bm25_search(query, k=fetch_k)
        bm25_docs = [doc for doc, _ in bm25_results]

        # Reciprocal Rank Fusion
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

        # Sort by RRF score
        sorted_keys = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        merged = [doc_map[key] for key in sorted_keys if key in doc_map][:fetch_k]

        # Re-rank with FlashRank
        final = self._rerank(query, merged, top_k=k)

        logger.info(
            f"Hybrid: {len(dense_results)} dense + {len(bm25_docs)} BM25 "
            f"-> {len(merged)} merged -> {len(final)} final"
        )
        return final

    # ==========================================
    # QA Chain
    # ==========================================

    def _build_qa_chain(self):
        """Build ConversationalRetrievalChain as fallback."""
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
    # Main Answer Pipeline
    # ==========================================

    async def get_answer(self, query: str, chat_history: List[Tuple[str, str]]) -> dict:
        """
        Full pipeline:
        1. Classify query type
        2. Rewrite follow-ups
        3. Adaptive hybrid retrieval
        4. Build context + prompt
        5. Generate answer
        """
        if not self._initialized:
            self.initialize()

        try:
            # ── Step 1: Classify query
            query_type = self._classify_query(query)
            config = RETRIEVAL_CONFIG.get(query_type, RETRIEVAL_CONFIG["SIMPLE"])

            logger.info(f"Pipeline: type={query_type}, top_k={config['top_k']}, skip={config['skip_retrieval']}")

            # ── Step 2: Handle greetings and out-of-scope (no retrieval needed)
            if config["skip_retrieval"]:
                context = "No document context needed for this response."
                # For greetings, use a minimal prompt
                if query_type == "GREETING":
                    response = self._llm.invoke(
                        f"You are the eClerx KYC Assistant. The user said: \"{query}\". "
                        f"Respond warmly and naturally, then offer to help with KYC documents. "
                        f"Keep it to 1–2 sentences."
                    )
                else:
                    response = self._llm.invoke(
                        f"You are the eClerx KYC Assistant. The user asked: \"{query}\". "
                        f"This is outside your scope. Politely say you're designed for KYC document queries only "
                        f"and offer to help with document questions. Keep it friendly and brief."
                    )
                return {
                    "answer": response.content,
                    "source_documents": [],
                    "query_type": query_type,
                }

            # ── Step 3: Rewrite follow-up questions
            search_query = self._rewrite_query(query, chat_history)

            # ── Step 4: Hybrid retrieval with adaptive top_k
            relevant_docs = self.hybrid_search(search_query, k=config["top_k"])

            # ── Step 5: Build context
            context = "\n\n---\n\n".join(doc.page_content for doc in relevant_docs)

            # If no context found, provide a hint
            if not context.strip():
                context = "[No relevant document sections were found for this query.]"

            # ── Step 6: Format chat history
            history_str = ""
            for human, ai in chat_history[-settings.MAX_MEMORY_MESSAGES:]:
                history_str += f"Human: {human}\nAssistant: {ai}\n\n"

            # ── Step 7: Generate answer
            prompt = PromptTemplate(
                template=QA_PROMPT,
                input_variables=["context", "chat_history", "question"],
            )
            formatted = prompt.format(
                context=context,
                chat_history=history_str,
                question=query,  # Use original query (not rewritten) so the answer addresses the user's words
            )
            response = self._llm.invoke(formatted)

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


# Singleton
rag_service = RAGService()

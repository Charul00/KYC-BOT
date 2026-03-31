"""
FastAPI Application Entry Point
KYC Document Chatbot - Production-Level RAG Architecture
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Fix socks proxy env vars that crash httpx (used by openai SDK)
for _k in list(os.environ.keys()):
    if "proxy" in _k.lower() and "socks" in os.environ.get(_k, "").lower():
        del os.environ[_k]

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Allow running `uvicorn main:app` from `backend/app` by exposing project root.
if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from app.config import settings
from app.routers.chat import router as chat_router
from app.services.rag_service import rag_service
from app.models.schemas import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ========================
# Application Lifespan
# ========================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting KYC Chatbot API...")
    try:
        rag_service.initialize()
        logger.info("RAG Service initialized. Ready to accept requests.")
    except Exception as e:
        logger.error(f"Failed to initialize RAG service: {e}")
        logger.warning("API will start but chat functionality may not work until fixed.")

    yield

    logger.info("Shutting down KYC Chatbot API...")


# ========================
# FastAPI App
# ========================

app = FastAPI(
    title="eClerx KYC Document Chatbot API",
    description="Production-level RAG-based chatbot API for KYC documents.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware — dynamically include FRONTEND_URL if set
cors_origins = list(settings.CORS_ORIGINS)
if settings.FRONTEND_URL:
    # Add the exact Vercel URL for production
    if settings.FRONTEND_URL not in cors_origins:
        cors_origins.append(settings.FRONTEND_URL)
    # Also allow the URL without trailing slash and vice versa
    alt = settings.FRONTEND_URL.rstrip("/")
    if alt not in cors_origins:
        cors_origins.append(alt)

# For demo/dev: if no FRONTEND_URL is configured, allow all origins
use_allow_all = not settings.FRONTEND_URL

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if use_allow_all else cors_origins,
    allow_credentials=not use_allow_all,  # credentials can't be used with wildcard
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])


# ========================
# Root & Health Endpoints
# ========================

@app.get("/")
async def root():
    return {
        "message": "eClerx KYC Document Chatbot API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        documents_loaded=rag_service.get_document_count(),
        vector_store_ready=rag_service.is_ready(),
    )

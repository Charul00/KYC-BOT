"""
Chat API Router - Production-level endpoints.
"""

import logging
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from openai import AuthenticationError

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    SourceDocument,
    DocumentUploadResponse,
    ClearSessionResponse,
    SessionInfo,
)
from app.services.rag_service import rag_service
from app.services.memory_service import memory_service
from app.services.document_service import document_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ========================
# Chat Endpoints
# ========================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint with hybrid retrieval + re-ranking."""
    try:
        chat_history = memory_service.get_chat_history(request.session_id)

        result = await rag_service.get_answer(
            query=request.query,
            chat_history=chat_history,
        )

        answer = result["answer"]
        source_docs = result.get("source_documents", [])
        query_type = result.get("query_type", "SIMPLE")
        logger.info(f"Query type: {query_type} | Sources: {len(source_docs)} | Answer length: {len(answer)}")

        memory_service.add_exchange(
            session_id=request.session_id,
            human_message=request.query,
            ai_message=answer,
        )

        sources = []
        for doc in source_docs:
            sources.append(
                SourceDocument(
                    content=doc.page_content[:300] + "..."
                    if len(doc.page_content) > 300
                    else doc.page_content,
                    metadata=doc.metadata,
                )
            )

        return ChatResponse(
            answer=answer,
            sources=sources,
            session_id=request.session_id,
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        error_message = str(e)

        if isinstance(e, AuthenticationError) or "invalid_api_key" in error_message or "Incorrect API key provided" in error_message:
            logger.error("Authentication error: invalid OpenAI API key.")
            raise HTTPException(
                status_code=401,
                detail="Authentication failed. Please contact the administrator to verify the API configuration.",
            )

        if "rate_limit" in error_message.lower() or "429" in error_message:
            logger.error(f"Rate limit error: {e}")
            raise HTTPException(
                status_code=429,
                detail="The service is currently experiencing high demand. Please try again in a moment.",
            )

        if "model_not_found" in error_message.lower() or "does not exist" in error_message.lower():
            logger.error(f"Model error: {e}")
            raise HTTPException(
                status_code=503,
                detail="The AI model is temporarily unavailable. Please try again shortly.",
            )

        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while processing your question. Please try again.",
        )


# ========================
# Document Endpoints (Multi-file upload)
# ========================

@router.post("/documents/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Upload one or multiple KYC documents.
    Each file is processed, chunked, and added to the vector store.
    Returns summary per file.
    """
    results = []
    errors = []

    for file in files:
        try:
            result = await document_service.upload_document(file)
            results.append({
                "filename": result["filename"],
                "status": "success",
                "message": f"Processed successfully",
            })
        except ValueError as e:
            errors.append({"filename": file.filename, "status": "error", "message": str(e)})
        except Exception as e:
            logger.error(f"Upload error for {file.filename}: {e}")
            errors.append({
                "filename": file.filename,
                "status": "error",
                "message": "Failed to process this document. Please try again.",
            })

    return {
        "processed": results,
        "errors": errors,
        "total_processed": len(results),
        "total_errors": len(errors),
    }


@router.get("/documents")
async def list_documents():
    """List all uploaded KYC documents."""
    return {"documents": document_service.list_documents()}


# ========================
# Session Endpoints
# ========================

@router.post("/sessions/new")
async def create_session():
    """Create a new chat session."""
    session_id = str(uuid.uuid4())[:8]
    memory_service.get_or_create_session(session_id)
    return {"session_id": session_id}


@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions():
    """List all active chat sessions."""
    sessions = memory_service.list_sessions()
    return [
        SessionInfo(
            session_id=s["session_id"],
            message_count=s["message_count"],
            created_at=s["created_at"],
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """Get chat history for a session."""
    history = memory_service.get_chat_history(session_id)
    return {
        "session_id": session_id,
        "history": [{"human": h, "ai": a} for h, a in history],
    }


@router.delete("/sessions/{session_id}", response_model=ClearSessionResponse)
async def clear_session(session_id: str):
    """Clear a session's conversation history."""
    memory_service.clear_session(session_id)
    return ClearSessionResponse(
        session_id=session_id,
        message="Session cleared.",
    )

"""
Chat API Router - Production-level endpoints.
"""

import json
import logging
import uuid
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
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
# Streaming Chat Endpoint (PRIMARY — low latency)
# ========================

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming SSE chat endpoint.
    Sends tokens as they are generated — user sees first word in ~1s.
    Protocol: text/event-stream, each line: data: <json>\n\n
    Final event: {"done": true, "sources": [...], "query_type": "..."}
    """
    chat_history = memory_service.get_chat_history(request.session_id)
    full_answer_tokens: List[str] = []

    async def event_generator():
        nonlocal full_answer_tokens
        try:
            async for chunk in rag_service.stream_answer(
                query=request.query,
                chat_history=chat_history,
            ):
                if chunk.get("done"):
                    # Save full answer to memory before sending the done event
                    full_answer = "".join(full_answer_tokens)
                    try:
                        memory_service.add_exchange(
                            session_id=request.session_id,
                            human_message=request.query,
                            ai_message=full_answer,
                        )
                    except Exception as mem_err:
                        logger.warning(f"Memory save failed: {mem_err}")

                    logger.info(
                        f"Stream complete | type={chunk.get('query_type')} | "
                        f"len={len(full_answer)} | sources={len(chunk.get('sources', []))}"
                    )
                    yield f"data: {json.dumps(chunk)}\n\n"
                else:
                    token = chunk.get("token", "")
                    if token:
                        full_answer_tokens.append(token)
                    yield f"data: {json.dumps(chunk)}\n\n"

        except Exception as e:
            logger.error(f"Stream generation error: {e}")
            error_payload = {
                "token": "Sorry, I encountered an error. Please try again.",
                "done": False,
            }
            yield f"data: {json.dumps(error_payload)}\n\n"
            yield f"data: {json.dumps({'done': True, 'sources': [], 'query_type': 'SIMPLE'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",   # Disable Nginx buffering on Render
        },
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
                "message": "Processed successfully",
                "chunks_created": result.get("chunks_created", 0),
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

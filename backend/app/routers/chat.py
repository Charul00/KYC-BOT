"""
Chat API Router - Production-level endpoints with dynamic routing and orchestration.
"""

import json
import logging
import uuid
from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from openai import AuthenticationError

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    SourceDocument,
    ClearSessionResponse,
    SessionInfo,
)
from app.services.rag_service import rag_service
from app.services.memory_service import memory_service
from app.services.document_service import document_service
from app.services.excel_service import excel_query_service
from app.services.router_service import router_service
from app.services.rule_service import rule_execution_service
from app.services.orchestrator_service import orchestrator_service
from app.services.file_registry_service import file_registry_service
from app.services.job_service import job_service
from app.services.ingestion_service import ingestion_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _merge_mixed_answer(excel_answer: str, rag_answer: str) -> str:
    return (
        "From the uploaded structured data:\n"
        f"{excel_answer}\n\n"
        "From the uploaded document context:\n"
        f"{rag_answer}"
    )


# ========================
# Chat Endpoints
# ========================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        chat_history = memory_service.get_chat_history(request.session_id)

        result = await orchestrator_service.answer_query(
            query=request.query,
            session_id=request.session_id,
            chat_history=chat_history,
            memory_service=memory_service,
        )

        answer = result["answer"]
        source_docs = result.get("source_documents", [])
        route_type = result.get("route_type", "RAG_QUERY")
        query_type = result.get("query_type", "SIMPLE")

        logger.info(
            f"Route: {route_type} | Query type: {query_type} | "
            f"Sources: {len(source_docs)} | Answer length: {len(answer)}"
        )

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
# Streaming Chat Endpoint
# ========================

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    chat_history = memory_service.get_chat_history(request.session_id)
    full_answer_tokens: List[str] = []

    async def event_generator():
        nonlocal full_answer_tokens
        try:
            route_type = router_service.route_query(
                request.query,
                chat_history=chat_history,
                source_summary=file_registry_service.get_source_summary(),
            )

            if route_type == "RULE_QUERY":
                answer = rule_execution_service.answer_query(request.query)
                memory_service.add_exchange(
                    session_id=request.session_id,
                    human_message=request.query,
                    ai_message=answer,
                )
                yield f"data: {json.dumps({'token': answer, 'done': False})}\n\n"
                yield f"data: {json.dumps({'done': True, 'sources': [], 'query_type': 'RULE_QUERY'})}\n\n"
                return

            if route_type == "EXCEL_QUERY":
                answer = excel_query_service.answer_query(
                    request.query,
                    session_id=request.session_id,
                    memory_service=memory_service,
                )
                memory_service.add_exchange(
                    session_id=request.session_id,
                    human_message=request.query,
                    ai_message=answer,
                )
                yield f"data: {json.dumps({'token': answer, 'done': False})}\n\n"
                yield f"data: {json.dumps({'done': True, 'sources': [], 'query_type': 'EXCEL_QUERY'})}\n\n"
                return

            if route_type == "MIXED_QUERY":
                excel_answer = excel_query_service.answer_query(
                    request.query,
                    session_id=request.session_id,
                    memory_service=memory_service,
                )

                rag_result = await rag_service.get_answer(
                    query=request.query,
                    chat_history=chat_history,
                )
                rag_answer = rag_result["answer"]
                source_docs = rag_result.get("source_documents", [])

                answer = _merge_mixed_answer(excel_answer, rag_answer)

                memory_service.add_exchange(
                    session_id=request.session_id,
                    human_message=request.query,
                    ai_message=answer,
                )

                sources = [
                    {
                        "content": doc.page_content[:300] + "..."
                        if len(doc.page_content) > 300
                        else doc.page_content,
                        "metadata": doc.metadata,
                    }
                    for doc in source_docs
                ]

                yield f"data: {json.dumps({'token': answer, 'done': False})}\n\n"
                yield f"data: {json.dumps({'done': True, 'sources': sources, 'query_type': 'MIXED_QUERY'})}\n\n"
                return

            async for chunk in rag_service.stream_answer(
                query=request.query,
                chat_history=chat_history,
            ):
                if chunk.get("done"):
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
                        f"Stream complete | route={route_type} | type={chunk.get('query_type')} | "
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
            "X-Accel-Buffering": "no",
        },
    )


# ========================
# Async Document Endpoints
# ========================

@router.post("/documents/upload-async")
async def upload_documents_async(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    jobs = []
    errors = []

    for file in files:
        try:
            saved = await document_service.save_uploaded_file(file)

            job = job_service.create_job(
                filename=saved["filename"],
                file_type=saved["file_type"],
                file_size_mb=saved["file_size_mb"],
            )

            background_tasks.add_task(
                ingestion_service.process_job,
                job["job_id"],
                saved["file_path"],
            )

            jobs.append(job)

        except ValueError as e:
            errors.append({
                "filename": file.filename,
                "status": "error",
                "message": str(e),
            })
        except Exception as e:
            logger.error(f"Async upload error for {file.filename}: {e}")
            errors.append({
                "filename": file.filename,
                "status": "error",
                "message": "Failed to queue this document for processing.",
            })

    return {
        "jobs": jobs,
        "errors": errors,
        "queued": len(jobs),
        "total_errors": len(errors),
    }


@router.get("/documents/status/{job_id}")
async def get_document_job_status(job_id: str):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.get("/documents/jobs")
async def list_document_jobs():
    return {"jobs": job_service.list_jobs()}


# ========================
# Legacy Sync Document Endpoints
# ========================

@router.post("/documents/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
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
    return {"documents": document_service.list_documents()}


@router.get("/documents/download/{filename}")
async def download_document(filename: str):
    """Download a file from the documents directory."""
    from fastapi.responses import FileResponse
    from app.config import settings
    import pathlib

    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    file_path = pathlib.Path(settings.DOCUMENTS_DIR) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )


@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    """
    Fully delete a document: removes chunks from ChromaDB + BM25,
    cleans the file registry, and deletes the file from disk.
    """
    # Basic path-traversal guard
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    result = document_service.delete_document(filename)
    if not result["deleted"]:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found.")

    return {
        "success": True,
        "filename": filename,
        "chunks_removed": result["chunks_removed"],
        "message": f"'{filename}' deleted. {result['chunks_removed']} chunks removed from the knowledge base.",
    }


# ========================
# Session Endpoints
# ========================

@router.post("/sessions/new")
async def create_session():
    session_id = str(uuid.uuid4())[:8]
    memory_service.get_or_create_session(session_id)
    return {"session_id": session_id}


@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions():
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
    history = memory_service.get_chat_history(session_id)
    return {
        "session_id": session_id,
        "history": [{"human": h, "ai": a} for h, a in history],
    }


@router.delete("/sessions/{session_id}", response_model=ClearSessionResponse)
async def clear_session(session_id: str):
    memory_service.clear_session(session_id)
    return ClearSessionResponse(
        session_id=session_id,
        message="Session cleared.",
    )
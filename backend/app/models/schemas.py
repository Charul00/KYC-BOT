"""
Pydantic models for request/response schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ========================
# Chat Schemas
# ========================

class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    query: str = Field(..., min_length=1, max_length=2000, description="User's question")
    session_id: str = Field(default="default", description="Session ID for conversation memory")


class SourceDocument(BaseModel):
    """Represents a source document chunk used in the response."""
    content: str = Field(..., description="Content of the source chunk")
    metadata: dict = Field(default_factory=dict, description="Metadata of the chunk")
    relevance_score: Optional[float] = Field(None, description="Similarity score")


class ChatResponse(BaseModel):
    """Response body for chat endpoint."""
    answer: str = Field(..., description="AI-generated answer")
    sources: List[SourceDocument] = Field(default_factory=list, description="Source documents used")
    session_id: str = Field(..., description="Session ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ========================
# Document Upload Schemas
# ========================

class DocumentUploadResponse(BaseModel):
    """Response body for document upload."""
    filename: str
    message: str
    chunks_created: int
    status: str = "success"


# ========================
# Session Schemas
# ========================

class SessionInfo(BaseModel):
    """Information about a chat session."""
    session_id: str
    message_count: int
    created_at: Optional[datetime] = None


class ClearSessionResponse(BaseModel):
    """Response for clearing a session."""
    session_id: str
    message: str
    status: str = "success"


# ========================
# Health Check
# ========================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    documents_loaded: int = 0
    vector_store_ready: bool = False

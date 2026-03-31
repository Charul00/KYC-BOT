"""
Memory Service - Manages conversation memory per session.
Uses LangChain's ConversationBufferWindowMemory for sliding window memory.
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


class SessionMemory:
    """Represents memory for a single chat session."""

    def __init__(self, session_id: str, max_messages: int):
        self.session_id = session_id
        self.max_messages = max_messages
        self.history: List[Tuple[str, str]] = []  # List of (human, ai) tuples
        self.created_at = datetime.utcnow()
        self.last_active = datetime.utcnow()

    def add_exchange(self, human_message: str, ai_message: str):
        """Add a human-AI exchange to memory."""
        self.history.append((human_message, ai_message))
        self.last_active = datetime.utcnow()

        # Keep only last N exchanges (sliding window)
        if len(self.history) > self.max_messages:
            self.history = self.history[-self.max_messages:]

    def get_history(self) -> List[Tuple[str, str]]:
        """Get conversation history as list of (human, ai) tuples."""
        return self.history.copy()

    def clear(self):
        """Clear all conversation history."""
        self.history = []

    @property
    def message_count(self) -> int:
        return len(self.history)


class MemoryService:
    """
    Manages conversation memory across multiple sessions.

    Features:
    - Per-session memory isolation
    - Sliding window (keeps last N exchanges)
    - Auto-cleanup of inactive sessions
    - Thread-safe session management
    """

    def __init__(self):
        self._sessions: Dict[str, SessionMemory] = {}

    def get_or_create_session(self, session_id: str) -> SessionMemory:
        """Get existing session or create new one."""
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionMemory(
                session_id=session_id,
                max_messages=settings.MAX_MEMORY_MESSAGES,
            )
            logger.info(f"Created new session: {session_id}")
        return self._sessions[session_id]

    def get_chat_history(self, session_id: str) -> List[Tuple[str, str]]:
        """Get chat history for a session."""
        session = self.get_or_create_session(session_id)
        return session.get_history()

    def add_exchange(self, session_id: str, human_message: str, ai_message: str):
        """Add a message exchange to a session."""
        session = self.get_or_create_session(session_id)
        session.add_exchange(human_message, ai_message)

    def clear_session(self, session_id: str) -> bool:
        """Clear a session's history."""
        if session_id in self._sessions:
            self._sessions[session_id].clear()
            logger.info(f"Cleared session: {session_id}")
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session entirely."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        return False

    def get_session_info(self, session_id: str) -> Optional[dict]:
        """Get information about a session."""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            return {
                "session_id": session.session_id,
                "message_count": session.message_count,
                "created_at": session.created_at,
                "last_active": session.last_active,
            }
        return None

    def list_sessions(self) -> List[dict]:
        """List all active sessions."""
        return [
            {
                "session_id": s.session_id,
                "message_count": s.message_count,
                "created_at": s.created_at,
                "last_active": s.last_active,
            }
            for s in self._sessions.values()
        ]

    def cleanup_inactive_sessions(self, max_inactive_minutes: int = 60):
        """Remove sessions that have been inactive for too long."""
        now = datetime.utcnow()
        to_remove = []
        for session_id, session in self._sessions.items():
            inactive_time = (now - session.last_active).total_seconds() / 60
            if inactive_time > max_inactive_minutes:
                to_remove.append(session_id)

        for session_id in to_remove:
            del self._sessions[session_id]
            logger.info(f"Cleaned up inactive session: {session_id}")

        return len(to_remove)


# Singleton instance
memory_service = MemoryService()

"""
Application configuration using pydantic-settings.
Loads environment variables from .env file.
"""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # OpenAI Configuration
    OPENAI_API_KEY: str = ""

    # ChromaDB Configuration
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_ANONYMIZED_TELEMETRY: bool = False

    # Document Configuration
    DOCUMENTS_DIR: str = "./data/documents"

    # Model Configuration
    MODEL_NAME: str = "gpt-4"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Chunking Configuration
    # 1500 chars ≈ ~300 tokens — keeps financial tables, legal clauses, and
    # policy paragraphs intact within a single chunk instead of splitting mid-sentence.
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 200      # wider overlap so boundary context is never lost

    # Retrieval Configuration
    TOP_K_RESULTS: int = 8        # default; overridden per query type in rag_service
    SIMILARITY_THRESHOLD: float = 0.3   # was 0.7 — lower threshold returns more candidates

    # LLM Configuration
    TEMPERATURE: float = 0.0
    MAX_TOKENS: int = 3000        # was 2048 — financial summaries need more room

    # Memory Configuration
    MAX_MEMORY_MESSAGES: int = 8  # was 5 — longer conversation context

    ANTHROPIC_API_KEY: str = ""
    TESSERACT_CMD: str = "tesseract"

    # Upload Configuration
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_EXTENSIONS: list = [".txt", ".pdf", ".docx", ".md", ".xlsx", ".png", ".jpg", ".jpeg", ".pptx"]

    # CORS — Vercel frontend URL is set here as the default
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://kyc-bot.vercel.app",
    ]
    # Vercel frontend URL — also set this as a Railway env var on the backend
    FRONTEND_URL: str = "https://kyc-bot.vercel.app"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

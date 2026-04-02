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
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # Retrieval Configuration
    TOP_K_RESULTS: int = 6
    SIMILARITY_THRESHOLD: float = 0.7

    # LLM Configuration
    TEMPERATURE: float = 0.0
    MAX_TOKENS: int = 2048

    # Memory Configuration
    MAX_MEMORY_MESSAGES: int = 5

    # Upload Configuration
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: list = [".txt", ".pdf", ".docx", ".md", ".xlsx"]

    # CORS — add your Vercel URL after deploying
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    # Set this env var on Render after you deploy frontend to Vercel
    # Example: https://kyc-chatbot-eclerx.vercel.app
    FRONTEND_URL: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

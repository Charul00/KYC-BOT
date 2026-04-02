"""
Document Service - Handles document upload, processing, and management.
Supports TXT, PDF, DOCX, and MD file formats.
"""

import os
import logging
import shutil
from typing import Optional
from pathlib import Path

from langchain.schema import Document
from fastapi import UploadFile

from app.config import settings
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)


class DocumentService:
    """
    Manages document uploads and processing.

    Features:
    - Multi-format support (TXT, PDF, DOCX, MD)
    - File validation (size, extension)
    - Automatic chunking and embedding via RAG service
    - Document listing and management
    """

    def __init__(self):
        self.docs_dir = Path(settings.DOCUMENTS_DIR)
        self.docs_dir.mkdir(parents=True, exist_ok=True)

    async def upload_document(self, file: UploadFile) -> dict:
        """
        Upload and process a new document.

        Steps:
        1. Validate file (extension, size)
        2. Save to documents directory
        3. Extract text content
        4. Chunk and add to vector store
        """
        # Validate extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {file_ext}. "
                f"Allowed: {settings.ALLOWED_EXTENSIONS}"
            )

        # Read file content
        content = await file.read()

        # Validate size
        size_mb = len(content) / (1024 * 1024)
        if size_mb > settings.MAX_UPLOAD_SIZE_MB:
            raise ValueError(
                f"File too large: {size_mb:.1f}MB. "
                f"Maximum: {settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        # Save file
        file_path = self.docs_dir / file.filename
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"Saved document: {file.filename} ({size_mb:.2f}MB)")

        # Extract text
        text = self._extract_text(file_path, file_ext)

        if not text.strip():
            raise ValueError("Could not extract any text from the document.")

        # Create LangChain document
        doc = Document(
            page_content=text,
            metadata={
                "source": file.filename,
                "file_type": file_ext,
                "file_path": str(file_path),
                "uploaded": True,
            },
        )

        # Add to vector store
        chunks_created = rag_service.add_documents([doc])

        return {
            "filename": file.filename,
            "chunks_created": chunks_created,
            "file_size_mb": round(size_mb, 2),
        }

    def _extract_text(self, file_path: Path, file_ext: str) -> str:
        """Extract text from a document based on its file type."""
        try:
            if file_ext in [".txt", ".md"]:
                return file_path.read_text(encoding="utf-8")

            elif file_ext == ".pdf":
                from pypdf import PdfReader
                reader = PdfReader(str(file_path))
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text

            elif file_ext == ".docx":
                import zipfile
                import xml.etree.ElementTree as ET

                text_parts = []
                with zipfile.ZipFile(str(file_path)) as z:
                    with z.open("word/document.xml") as f:
                        tree = ET.parse(f)
                        root = tree.getroot()
                        for t_elem in root.iter(
                            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
                        ):
                            if t_elem.text:
                                text_parts.append(t_elem.text)
                return " ".join(text_parts)

            elif file_ext == ".xlsx":
                import openpyxl
                wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
                text_parts = []
                for sheet in wb.worksheets:
                    text_parts.append(f"[Sheet: {sheet.title}]")
                    for row in sheet.iter_rows(values_only=True):
                        row_text = "  |  ".join(str(c) for c in row if c is not None)
                        if row_text.strip():
                            text_parts.append(row_text)
                wb.close()
                return "\n".join(text_parts)

            else:
                raise ValueError(f"Unsupported file type: {file_ext}")

        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            raise

    def list_documents(self) -> list:
        """List all documents in the documents directory."""
        documents = []
        for file_path in self.docs_dir.iterdir():
            if file_path.suffix.lower() in settings.ALLOWED_EXTENSIONS:
                stat = file_path.stat()
                documents.append({
                    "filename": file_path.name,
                    "file_type": file_path.suffix,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": stat.st_mtime,
                })
        return documents

    def delete_document(self, filename: str) -> bool:
        """Delete a document from the documents directory."""
        file_path = self.docs_dir / filename
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted document: {filename}")
            return True
        return False


# Singleton instance
document_service = DocumentService()

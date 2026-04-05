"""
Document Service - Handles document upload, processing, and management.
Supports TXT, PDF, DOCX, MD, XLSX, PNG, JPG, JPEG, and PPTX file formats.

Key design decisions:
  - PDFs are extracted page-by-page for accurate citations (one Document per page).
  - pdfplumber is opened ONCE per PDF (not once per page) for efficiency.
  - Tesseract is OPTIONAL — if not installed, OCR steps are silently skipped.
  - Vision (Claude) is OPTIONAL and is used conservatively (only on pages
    where text density is very low AND the page area is large enough to
    contain a meaningful chart/graph). Errors are caught silently.
"""

import logging
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from langchain.schema import Document
from fastapi import UploadFile

from app.config import settings
from app.services.rag_service import rag_service
from app.services.excel_service import excel_query_service
from app.services.rule_service import rule_execution_service
from app.services.file_registry_service import file_registry_service
from app.services.image_preprocessor import image_preprocessor
from app.services.ocr_service import ocr_service
from app.services.vision_service import vision_service
from app.services.image_merge_service import image_merge_service
from app.services.ppt_service import ppt_service

logger = logging.getLogger(__name__)

# ── Tesseract availability (from ocr_service which already checks it) ─────────
# We read the same flag so document_service doesn't crash at import time.
try:
    from app.services.ocr_service import _TESSERACT_AVAILABLE as _OCR_AVAILABLE
except ImportError:
    _OCR_AVAILABLE = False

# ── pdfplumber availability ───────────────────────────────────────────────────
try:
    import pdfplumber as _pdfplumber_module
    _HAS_PDFPLUMBER = True
except ImportError:
    _pdfplumber_module = None  # type: ignore[assignment]
    _HAS_PDFPLUMBER = False
    logger.warning(
        "pdfplumber not installed — table extraction disabled. "
        "Fix: pip install pdfplumber==0.11.4 --break-system-packages"
    )

# How few characters per (width × height) pixel-unit before we consider
# a page potentially chart-heavy and worth running vision on.
# Raised from 0.02 → 0.005 so vision is only used on truly sparse pages.
_CHART_DENSITY_THRESHOLD = 0.005
# Minimum raw-text length on a page before calling vision at all.
# Pages with zero text are likely scanned (handled separately) or blank.
_CHART_MIN_TEXT_LEN = 30
# Maximum number of vision API calls per PDF to avoid rate-limit / cost issues.
_MAX_VISION_CALLS_PER_PDF = 15


class DocumentService:
    """
    Manages document uploads and processing.
    """

    def __init__(self):
        self.docs_dir = Path(settings.DOCUMENTS_DIR)
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        # Set tesseract path if configured — but don't crash if it's missing.
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        except Exception:
            pass  # OCR service already logs a warning

    # ──────────────────────────────────────────────────────────────────────────
    # Upload helpers
    # ──────────────────────────────────────────────────────────────────────────

    async def save_uploaded_file(self, file: UploadFile) -> dict:
        """Save file only. No heavy processing here (used by async ingestion)."""
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {file_ext}. Allowed: {settings.ALLOWED_EXTENSIONS}"
            )

        content = await file.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > settings.MAX_UPLOAD_SIZE_MB:
            raise ValueError(
                f"File too large: {size_mb:.1f}MB. Maximum: {settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        file_path = self.docs_dir / file.filename
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"Saved upload only: {file.filename} ({size_mb:.2f}MB)")
        return {
            "filename": file.filename,
            "file_path": str(file_path),
            "file_type": file_ext,
            "file_size_mb": round(size_mb, 2),
        }

    async def upload_document(self, file: UploadFile) -> dict:
        """Backward-compatible sync upload + processing."""
        saved = await self.save_uploaded_file(file)
        result = self.process_saved_file(Path(saved["file_path"]))
        return {
            "filename": saved["filename"],
            "chunks_created": result.get("chunks_created", 0),
            "file_size_mb": saved["file_size_mb"],
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Core processing
    # ──────────────────────────────────────────────────────────────────────────

    def process_saved_file(self, file_path: Path, progress_callback=None) -> dict:
        """
        Heavy processing for an already-saved file.
        PDFs → page-level Documents (one per page) for accurate citations.
        All other formats → single Document.

        progress_callback(pct, stage, message) is called throughout so the
        job tracker can report real percentage progress to the frontend.
        """
        def _prog(pct: int, stage: str, message: str = ""):
            if progress_callback:
                try:
                    progress_callback(pct, stage, message or stage)
                except Exception:
                    pass

        file_ext = file_path.suffix.lower()
        size_mb = file_path.stat().st_size / (1024 * 1024)

        _prog(5, "Reading file", f"Reading {file_path.name}…")

        if file_ext == ".pdf":
            _prog(8, "Extracting PDF", "Analysing PDF pages…")
            docs = self._extract_pdf_as_page_documents(file_path, progress_callback=_prog)
            if not docs:
                raise ValueError("Could not extract any text from the PDF.")
            full_text = "\n\n".join(d.page_content for d in docs)
        else:
            _prog(10, "Extracting text", f"Extracting content from {file_ext} file…")
            text, extra_metadata = self._extract_text_and_metadata(file_path, file_ext)
            if not text.strip():
                raise ValueError("Could not extract any text from the document.")
            docs = [
                Document(
                    page_content=text,
                    metadata={
                        "source": file_path.name,
                        "file_type": file_ext,
                        "file_path": str(file_path),
                        "uploaded": True,
                        **extra_metadata,
                    },
                )
            ]
            full_text = text
            _prog(55, "Text extracted", "Preparing chunks…")

        _prog(65, "Chunking & embedding", "Splitting into chunks and building vector index…")
        if file_ext == ".xlsx":
            chunks_created = rag_service.add_documents_large(docs)
        else:
            chunks_created = rag_service.add_documents(docs)
        _prog(82, "Index built", f"{chunks_created} chunks indexed into vector store…")

        if file_ext == ".xlsx":
            _prog(85, "Refreshing Excel index", "Refreshing structured data index…")
            excel_query_service.refresh()

        _prog(90, "Refreshing rules", "Updating compliance rule cache…")
        rule_execution_service.refresh_rules()

        _prog(95, "Finalising", "Updating file registry…")
        file_registry_service.upsert_file(
            filename=file_path.name,
            file_type=file_ext,
            file_size_mb=round(size_mb, 2),
            extracted_text=full_text[:5000],
        )

        return {
            "filename": file_path.name,
            "chunks_created": chunks_created,
            "file_size_mb": round(size_mb, 2),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Non-PDF extraction routing
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_text_and_metadata(self, file_path: Path, file_ext: str):
        try:
            if file_ext in [".txt", ".md"]:
                return file_path.read_text(encoding="utf-8"), {}
            elif file_ext == ".pdf":
                return self._extract_pdf_with_scanned_fallback(file_path)
            elif file_ext == ".docx":
                return self._extract_docx_with_embedded_images(file_path)
            elif file_ext == ".xlsx":
                return self._extract_xlsx_text(file_path), {}
            elif file_ext in [".png", ".jpg", ".jpeg"]:
                return self._extract_image_text(file_path)
            elif file_ext == ".pptx":
                return ppt_service.extract_text_and_metadata(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            raise

    # ──────────────────────────────────────────────────────────────────────────
    # Image pipeline (used for standalone image uploads + DOCX embedded images)
    # ──────────────────────────────────────────────────────────────────────────

    def _run_image_pipeline(self, image_path: Path) -> Tuple[str, Dict[str, Any]]:
        """
        Full image pipeline: preprocess → OCR (if available) → vision → merge.
        Gracefully handles missing tesseract or vision failures.
        """
        bundle = image_preprocessor.preprocess(image_path)

        # OCR step — safe even when tesseract is missing (ocr_service returns empty dict)
        ocr_result = ocr_service.extract(bundle.grayscale_image, bundle.binary_image)

        # Vision step — safe even when API key is missing or call fails
        vision_result = vision_service.analyze(image_path)

        merged = image_merge_service.merge(bundle.quality, ocr_result, vision_result)

        metadata = {
            "doc_type": merged.get("doc_type", "unknown"),
            "image_pipeline": True,
            "overall_confidence": merged.get("overall_confidence", 0.0),
            "readability_score": bundle.quality.get("readability_score", 0.0),
            "face_present": merged.get("face_present", False),
        }

        return merged["merged_text"], metadata

    def _extract_image_text(self, file_path: Path):
        return self._run_image_pipeline(file_path)

    # ──────────────────────────────────────────────────────────────────────────
    # PDF extraction — page-level Documents
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_pdf_as_page_documents(self, file_path: Path, progress_callback=None) -> List[Document]:
        """
        Extract a PDF as a list of page-level Documents.

        Per-page content includes:
          1. Plain text via pypdf
          2. Markdown tables via pdfplumber (opened once for the whole PDF)
          3. Vision description of chart-heavy pages (conservative heuristic)
          4. OCR fallback for scanned (near-zero text) pages

        Metadata per Document:
          source, file_type, page_number, total_pages, document_title,
          has_tables, has_images, is_scanned_page
        """
        from pypdf import PdfReader
        import pypdfium2 as pdfium

        def _prog(pct: int, stage: str, message: str = ""):
            if progress_callback:
                try:
                    progress_callback(pct, stage, message or stage)
                except Exception:
                    pass

        reader = PdfReader(str(file_path))
        pdf_pdfium = pdfium.PdfDocument(str(file_path))
        total_pages = len(reader.pages)
        doc_title = self._detect_document_title(reader, file_path)

        logger.info(
            f"Starting PDF extraction: '{file_path.name}' "
            f"({total_pages} pages, pdfplumber={_HAS_PDFPLUMBER})"
        )

        # Open pdfplumber ONCE for the whole PDF (not once per page)
        plumb_pdf = None
        if _HAS_PDFPLUMBER:
            try:
                plumb_pdf = _pdfplumber_module.open(str(file_path))
            except Exception as exc:
                logger.warning(f"pdfplumber failed to open PDF: {exc}")

        # Track vision call budget
        vision_calls_used = 0

        try:
            page_documents: List[Document] = []

            for page_idx, page in enumerate(reader.pages):
                page_num = page_idx + 1
                page_parts: List[str] = []
                has_tables = False
                has_images = False

                # Report per-page progress: pages cover 8% → 60% of total progress
                page_pct = 8 + int((page_num / total_pages) * 52)
                _prog(
                    page_pct,
                    "Extracting PDF",
                    f"Page {page_num} of {total_pages}…",
                )

                # ── 1. Plain text ──────────────────────────────────────────
                raw_text = (page.extract_text() or "").strip()
                # A page is "scanned" when pypdf returns very little text
                is_scanned = len(raw_text) < 50

                # ── 2. pdfplumber table extraction ─────────────────────────
                if plumb_pdf and not is_scanned:
                    try:
                        plumb_page = plumb_pdf.pages[page_idx]
                        tables = plumb_page.extract_tables()
                        if tables:
                            has_tables = True
                            table_blocks: List[str] = []
                            for tbl in tables:
                                md_rows: List[str] = []
                                for row_idx, row in enumerate(tbl):
                                    clean_row = [
                                        str(c).strip() if c is not None else ""
                                        for c in row
                                    ]
                                    md_rows.append(
                                        "| " + " | ".join(clean_row) + " |"
                                    )
                                    if row_idx == 0:
                                        md_rows.append(
                                            "|" + "|".join(["---"] * len(clean_row)) + "|"
                                        )
                                table_blocks.append("\n".join(md_rows))
                            table_text = "\n\n".join(table_blocks)
                            page_parts.append(f"[Tables on page {page_num}]\n{table_text}")
                    except Exception as exc:
                        logger.debug(
                            f"pdfplumber table extraction failed on page {page_num}: {exc}"
                        )

                # ── 3. Assemble normal text ────────────────────────────────
                if raw_text and not is_scanned:
                    page_parts.insert(0, raw_text)   # text goes first

                # ── 4. Scanned page fallback (OCR + vision) ────────────────
                if is_scanned:
                    ocr_text = self._ocr_page(pdf_pdfium, page_idx, page_num)
                    if ocr_text:
                        page_parts.append(
                            f"[Scanned page {page_num} — OCR/vision analysis]\n{ocr_text}"
                        )
                        has_images = True
                    elif raw_text:
                        # Last resort: use whatever pypdf returned, however short
                        page_parts.append(raw_text)

                # ── 5. Chart / visual description (non-scanned pages only) ──
                # Use vision only when budget remains AND the page looks chart-heavy
                if (
                    not is_scanned
                    and vision_calls_used < _MAX_VISION_CALLS_PER_PDF
                ):
                    chart_desc = self._maybe_describe_page_visuals(
                        pdf_pdfium, page_idx, page_num, raw_text
                    )
                    if chart_desc:
                        has_images = True
                        vision_calls_used += 1
                        page_parts.append(
                            f"[Visual content on page {page_num}]\n{chart_desc}"
                        )

                # ── 6. Skip completely empty pages ─────────────────────────
                page_content = "\n\n".join(page_parts).strip()
                if not page_content:
                    continue

                page_documents.append(
                    Document(
                        page_content=(
                            f"[Page {page_num} of {total_pages} — {doc_title}]\n\n"
                            f"{page_content}"
                        ),
                        metadata={
                            "source": file_path.name,
                            "file_type": ".pdf",
                            "file_path": str(file_path),
                            "uploaded": True,
                            "page_number": page_num,
                            "total_pages": total_pages,
                            "document_title": doc_title,
                            "has_tables": has_tables,
                            "has_images": has_images,
                            "is_scanned_page": is_scanned,
                        },
                    )
                )

        finally:
            # Always close pdfplumber handle
            if plumb_pdf is not None:
                try:
                    plumb_pdf.close()
                except Exception:
                    pass

        logger.info(
            f"PDF '{file_path.name}': extracted {len(page_documents)}/{total_pages} pages "
            f"(tables={sum(1 for d in page_documents if d.metadata.get('has_tables'))}, "
            f"images={sum(1 for d in page_documents if d.metadata.get('has_images'))}, "
            f"vision_calls={vision_calls_used})"
        )
        return page_documents

    def _detect_document_title(self, reader, file_path: Path) -> str:
        """Best-effort document title from PDF metadata or filename."""
        try:
            meta = reader.metadata
            if meta and meta.get("/Title"):
                title = str(meta["/Title"]).strip()
                if title and len(title) > 3:
                    return title
        except Exception:
            pass
        return file_path.stem.replace("_", " ").replace("-", " ").title()

    def _ocr_page(self, pdf_pdfium, page_idx: int, page_num: int) -> str:
        """
        Render a scanned PDF page to an image and run OCR + vision on it.
        Returns extracted text string (may be empty if both fail).
        """
        try:
            pdf_page = pdf_pdfium.get_page(page_idx)
            pil_image = pdf_page.render(scale=2.0).to_pil()
            pdf_page.close()

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                pil_image.save(tmp_path, format="PNG")

            try:
                image_text, _ = self._run_image_pipeline(tmp_path)
                return image_text
            finally:
                tmp_path.unlink(missing_ok=True)

        except Exception as exc:
            logger.warning(f"OCR fallback failed on page {page_num}: {exc}")
            return ""

    def _maybe_describe_page_visuals(
        self,
        pdf_pdfium,
        page_idx: int,
        page_num: int,
        page_text: str,
    ) -> str:
        """
        Decide whether a page likely contains charts/graphs worth describing via vision,
        then call analyze_chart() if so.

        Heuristic: text density (chars per width×height pixel-unit) below threshold
        AND raw text is non-trivial (at least _CHART_MIN_TEXT_LEN chars).
        Pages with very short text are treated as scanned and handled separately.
        """
        if len(page_text) < _CHART_MIN_TEXT_LEN:
            return ""

        try:
            pdf_page = pdf_pdfium.get_page(page_idx)
            page_width = pdf_page.get_width()
            page_height = pdf_page.get_height()
            pdf_page.close()

            text_density = len(page_text) / max(page_width * page_height, 1)

            if text_density >= _CHART_DENSITY_THRESHOLD:
                return ""   # Text-dense page — no chart description needed

            # Page appears chart/image heavy — render and describe
            pdf_page = pdf_pdfium.get_page(page_idx)
            pil_image = pdf_page.render(scale=1.5).to_pil()
            pdf_page.close()

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                pil_image.save(tmp_path, format="PNG")

            try:
                description = vision_service.analyze_chart(tmp_path, page_num=page_num)
                if description and len(description) > 30:
                    logger.debug(
                        f"Vision description generated for page {page_num} "
                        f"(density={text_density:.6f})"
                    )
                    return description
            finally:
                tmp_path.unlink(missing_ok=True)

        except Exception as exc:
            logger.debug(f"Visual description skipped for page {page_num}: {exc}")

        return ""

    def _extract_pdf_with_scanned_fallback(self, file_path: Path):
        """Legacy method kept for backward compatibility."""
        docs = self._extract_pdf_as_page_documents(file_path)
        combined = "\n\n".join(d.page_content for d in docs)
        has_scanned = any(d.metadata.get("is_scanned_page") for d in docs)
        return combined, {"pdf_scanned_fallback_used": has_scanned}

    # ──────────────────────────────────────────────────────────────────────────
    # DOCX extraction
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_docx_with_embedded_images(self, file_path: Path):
        text_parts: List[str] = []

        with zipfile.ZipFile(str(file_path)) as z:
            with z.open("word/document.xml") as f:
                tree = ET.parse(f)
                root = tree.getroot()
                for t_elem in root.iter(
                    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
                ):
                    if t_elem.text:
                        text_parts.append(t_elem.text)

        embedded_image_texts = self._extract_docx_embedded_images(file_path)

        final_parts = []
        if text_parts:
            final_parts.append("[DOCX Text]")
            final_parts.append(" ".join(text_parts))

        if embedded_image_texts:
            final_parts.append("[DOCX Embedded Image Analysis]")
            final_parts.extend(embedded_image_texts)

        metadata = {"docx_embedded_images_count": len(embedded_image_texts)}
        return "\n\n".join(final_parts).strip(), metadata

    def _extract_docx_embedded_images(self, file_path: Path) -> List[str]:
        image_texts: List[str] = []

        with zipfile.ZipFile(str(file_path)) as z:
            media_files = [n for n in z.namelist() if n.startswith("word/media/")]

            for idx, media_name in enumerate(media_files, start=1):
                try:
                    suffix = Path(media_name).suffix.lower()
                    if suffix not in [".png", ".jpg", ".jpeg"]:
                        continue

                    with z.open(media_name) as img_file:
                        blob = img_file.read()

                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                        tmp.write(blob)
                        tmp_path = Path(tmp.name)

                    try:
                        image_text, _ = self._run_image_pipeline(tmp_path)
                        image_texts.append(f"[Embedded image {idx}]\n{image_text}")
                    finally:
                        try:
                            tmp_path.unlink(missing_ok=True)
                        except Exception:
                            pass

                except Exception as exc:
                    logger.warning(
                        f"Failed DOCX embedded image extraction for {media_name}: {exc}"
                    )

        return image_texts

    # ──────────────────────────────────────────────────────────────────────────
    # XLSX extraction
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_xlsx_text(self, file_path: Path) -> str:
        """
        Extract Excel content grouped into row-blocks so the text splitter
        produces far fewer, richer chunks instead of one chunk per row.

        Strategy:
        - Group every ROWS_PER_BLOCK rows into one text block
        - Repeat the header row at the top of every block for context
        - This reduces a 128k-row file from ~78k chunks down to ~2-4k chunks
        - Keeps all data retrievable while staying within OpenAI rate limits
        """
        import openpyxl

        ROWS_PER_BLOCK = 200  # rows grouped per chunk — larger = fewer chunks = fewer API calls

        wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
        text_parts = []

        for sheet in wb.worksheets:
            text_parts.append(f"\n[Sheet: {sheet.title}]")
            header: list = []
            data_rows: list = []

            for row_idx, row in enumerate(sheet.iter_rows(values_only=True)):
                row_text = "  |  ".join(str(c) for c in row if c is not None)
                if not row_text.strip():
                    continue
                if row_idx == 0:
                    header = row
                    text_parts.append("Columns: " + "  |  ".join(str(c) for c in header if c is not None))
                else:
                    data_rows.append(row_text)

                    # Flush a block every ROWS_PER_BLOCK rows
                    if len(data_rows) >= ROWS_PER_BLOCK:
                        header_line = "Columns: " + "  |  ".join(str(c) for c in header if c is not None)
                        block = f"[Sheet: {sheet.title}]\n{header_line}\n" + "\n".join(data_rows)
                        text_parts.append(block)
                        data_rows = []

            # Flush remaining rows
            if data_rows:
                header_line = "Columns: " + "  |  ".join(str(c) for c in header if c is not None)
                block = f"[Sheet: {sheet.title}]\n{header_line}\n" + "\n".join(data_rows)
                text_parts.append(block)

        wb.close()
        return "\n\n".join(text_parts)

    # ──────────────────────────────────────────────────────────────────────────
    # Document management
    # ──────────────────────────────────────────────────────────────────────────

    def list_documents(self) -> list:
        """
        List all uploaded documents, enriched with chunk counts from the file registry.
        """
        registry = {f["filename"]: f for f in file_registry_service.list_files()}
        documents = []
        for file_path in self.docs_dir.iterdir():
            if file_path.suffix.lower() in settings.ALLOWED_EXTENSIONS:
                stat = file_path.stat()
                reg = registry.get(file_path.name, {})
                documents.append({
                    "filename":   file_path.name,
                    "file_type":  file_path.suffix,
                    "size_mb":    round(stat.st_size / (1024 * 1024), 2),
                    "modified":   stat.st_mtime,
                    "role":       reg.get("role", "unknown"),
                    "uploaded_at": reg.get("uploaded_at", ""),
                })
        return documents

    def delete_document(self, filename: str) -> dict:
        """
        Fully removes a document:
          1. Deletes all chunks from ChromaDB + rebuilds BM25
          2. Removes from file registry
          3. Deletes the file from disk
        Returns a dict with deleted=True/False and chunks_removed count.
        """
        # 1. Remove from vector store (also rebuilds BM25)
        chunks_removed = rag_service.remove_documents_by_source(filename)

        # 2. Remove from file registry
        file_registry_service.remove_file(filename)

        # 3. Refresh Excel index if needed
        if filename.lower().endswith(".xlsx"):
            from app.services.excel_service import excel_query_service
            excel_query_service.refresh()

        # 4. Refresh rule cache
        from app.services.rule_service import rule_execution_service
        rule_execution_service.refresh_rules()

        # 5. Delete physical file
        file_path = self.docs_dir / filename
        file_existed = file_path.exists()
        if file_existed:
            file_path.unlink()

        logger.info(
            f"Deleted document '{filename}': "
            f"chunks_removed={chunks_removed}, file_existed={file_existed}"
        )
        return {
            "deleted": file_existed or chunks_removed > 0,
            "filename": filename,
            "chunks_removed": chunks_removed,
        }


document_service = DocumentService()

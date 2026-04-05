"""
Vision Service — OpenAI GPT-4o vision layer for KYC documents and PDF chart analysis.

Two modes:
  analyze()       — Identity / KYC document analysis (returns structured JSON fields)
  analyze_chart() — PDF page / chart / graph description (returns plain-text description)

Images are automatically resized + JPEG-compressed to stay under OpenAI's 20 MB limit.
All errors are caught and returned as graceful fallbacks so callers never crash.

Uses OpenAI GPT-4o vision (same API key already configured — no extra cost).
"""

import base64
import io
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Max dimension (pixels) before we resize. OpenAI recommends ≤2048px.
_MAX_IMAGE_PX = 1568
# Max raw image size (bytes) — OpenAI allows up to 20MB but we keep it low for speed
_MAX_IMAGE_BYTES = 4_900_000
# JPEG quality used when re-encoding for size reduction
_JPEG_QUALITY = 82


def _load_and_resize(file_path: Path) -> tuple:
    """
    Open image, resize if too large, re-encode as JPEG.
    Returns (base64_string, media_type).
    """
    from PIL import Image

    img = Image.open(file_path).convert("RGB")

    # Resize to fit within _MAX_IMAGE_PX on the longest side
    w, h = img.size
    if max(w, h) > _MAX_IMAGE_PX:
        scale = _MAX_IMAGE_PX / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Encode as JPEG
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
    data = buf.getvalue()

    # Reduce quality progressively if still too large
    quality = _JPEG_QUALITY
    while len(data) > _MAX_IMAGE_BYTES and quality > 40:
        quality -= 10
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        data = buf.getvalue()

    if len(data) > _MAX_IMAGE_BYTES:
        raise ValueError(
            f"Image is {len(data)//1024}KB even at quality={quality}; exceeds limit."
        )

    image_b64 = base64.b64encode(data).decode("utf-8")
    return image_b64, "image/jpeg"


class VisionService:
    """
    GPT-4o vision layer.

    analyze()       — KYC identity document → structured JSON.
    analyze_chart() — PDF page chart/graph → plain-text description string.
    """

    def __init__(self):
        self._client = None
        self._client_error: Optional[str] = None

    def _get_client(self):
        """Lazy-init OpenAI client."""
        if self._client is not None:
            return self._client
        if self._client_error:
            raise RuntimeError(self._client_error)

        try:
            from openai import OpenAI
            from app.config import settings

            api_key = getattr(settings, "OPENAI_API_KEY", None)
            if not api_key:
                self._client_error = "OPENAI_API_KEY not set — vision disabled."
                raise RuntimeError(self._client_error)

            self._client = OpenAI(api_key=api_key)
            logger.info("VisionService initialized with GPT-4o (OpenAI)")
            return self._client
        except ImportError as exc:
            self._client_error = f"openai package not installed: {exc}"
            raise RuntimeError(self._client_error)

    def _call(self, image_b64: str, prompt: str, max_tokens: int = 1800) -> str:
        """Make a single GPT-4o vision call. Returns raw text response."""
        client = self._get_client()

        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=max_tokens,
            temperature=0.0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                                "detail": "high",   # high = full 2048px resolution tiles
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )

        return response.choices[0].message.content or ""

    # ------------------------------------------------------------------
    # Public: KYC identity document analysis
    # ------------------------------------------------------------------

    def analyze(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyse a KYC identity document image (Aadhaar, PAN, passport, form, …).
        Returns structured JSON with doc_type, fields, tables, etc.
        On any error returns a safe empty result rather than raising.
        """
        try:
            image_b64, _ = _load_and_resize(file_path)

            prompt = (
                "You are a KYC document vision extractor.\n\n"
                "Return ONLY valid JSON with this schema:\n"
                "{\n"
                '  "doc_type": "aadhaar_card | pan_card | passport | bank_statement | '
                'process_screenshot | policy_screenshot | kyc_form | unknown",\n'
                '  "document_summary": "short summary of what this document shows",\n'
                '  "fields": {\n'
                '    "name": {"value": "", "confidence": 0.0},\n'
                '    "id_number": {"value": "", "confidence": 0.0},\n'
                '    "address": {"value": "", "confidence": 0.0},\n'
                '    "date_of_birth": {"value": "", "confidence": 0.0},\n'
                '    "document_type": {"value": "", "confidence": 0.0},\n'
                '    "issue_date": {"value": "", "confidence": 0.0},\n'
                '    "expiry_date": {"value": "", "confidence": 0.0}\n'
                "  },\n"
                '  "tables": [],\n'
                '  "risk_terms_detected": [],\n'
                '  "process_rules_detected": [],\n'
                '  "face_present": false,\n'
                '  "overall_confidence": 0.0,\n'
                '  "quality_notes": []\n'
                "}\n\n"
                "Rules:\n"
                "- If a field is missing, keep empty string and low confidence.\n"
                "- If image is a process/BRD screenshot, populate process_rules_detected.\n"
                "- Return JSON only — no markdown fences, no prose.\n"
            )

            raw = self._call(image_b64, prompt, max_tokens=1800).strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```", 2)[-1].lstrip("json").strip()
                if raw.endswith("```"):
                    raw = raw[:-3].strip()

            return json.loads(raw)

        except Exception as exc:
            logger.warning(f"vision_service.analyze() failed for {file_path}: {exc}")
            return self._empty_kyc_result()

    # ------------------------------------------------------------------
    # Public: PDF chart / graph description
    # ------------------------------------------------------------------

    def analyze_chart(self, file_path: Path, page_num: int = 0) -> str:
        """
        Analyse a PDF page image for charts, graphs, tables, and visual content.
        Returns a plain-text description string (suitable for RAG indexing).
        On any error returns empty string (caller skips gracefully).
        """
        try:
            image_b64, _ = _load_and_resize(file_path)

            page_ref = f"page {page_num}" if page_num else "this page"

            prompt = (
                f"You are analysing {page_ref} of a business document.\n\n"
                "This may be a flowchart, process diagram, decision tree, organisational chart, "
                "financial chart, or any other visual content.\n\n"
                "Describe ALL visual content in plain text. Follow these rules STRICTLY:\n\n"
                "1. FLOWCHARTS / PROCESS DIAGRAMS:\n"
                "   a. State the EXACT starting node text and its shape (e.g. parallelogram, oval, rectangle).\n"
                "   b. Count and list EVERY decision diamond — number them 1, 2, 3... with exact label text.\n"
                "   c. For EACH decision diamond state BOTH the Yes path AND the No path with exact destination text.\n"
                "   d. Trace the COMPLETE flow in strict order from start to end — do not skip any intermediate steps.\n"
                "   e. State the EXACT text and shape of the final/end node(s).\n"
                "   f. Note the COLOR of each shape type (e.g. 'decision diamonds are green', 'process boxes are blue', 'end node is pink/red').\n"
                "   g. Note the GEOMETRIC SHAPE of each node type (parallelogram=start/end, diamond=decision, rectangle=process, rounded rectangle=terminal).\n\n"
                "2. Charts or graphs — what they show, axes labels, and key data values or trends.\n"
                "3. Tables — column headers and important rows/values.\n"
                "4. Text callouts, annotations, or highlighted figures.\n\n"
                "Be exhaustive — include the EXACT TEXT from every shape/box in the diagram. "
                "Do NOT summarise or paraphrase the node labels. "
                "Write in clear numbered steps. Do NOT output JSON. "
                "Keep response under 1000 words.\n"
            )

            description = self._call(image_b64, prompt, max_tokens=1500).strip()

            if len(description) < 20:
                return ""

            logger.debug(f"Chart vision description generated for page {page_num}")
            return description

        except Exception as exc:
            logger.debug(
                f"vision_service.analyze_chart() skipped for {file_path} "
                f"(page {page_num}): {exc}"
            )
            return ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _empty_kyc_result(self) -> Dict[str, Any]:
        return {
            "doc_type": "unknown",
            "document_summary": "",
            "fields": {
                "name": {"value": "", "confidence": 0.0},
                "id_number": {"value": "", "confidence": 0.0},
                "address": {"value": "", "confidence": 0.0},
                "date_of_birth": {"value": "", "confidence": 0.0},
                "document_type": {"value": "", "confidence": 0.0},
                "issue_date": {"value": "", "confidence": 0.0},
                "expiry_date": {"value": "", "confidence": 0.0},
            },
            "tables": [],
            "risk_terms_detected": [],
            "process_rules_detected": [],
            "face_present": False,
            "overall_confidence": 0.0,
            "quality_notes": ["vision analysis unavailable"],
        }


vision_service = VisionService()

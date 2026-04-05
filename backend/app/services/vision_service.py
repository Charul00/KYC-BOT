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

    def _detect_image_category(self, file_path: Path) -> str:
        """
        First-pass GPT-4o call: classify what kind of visual this image is.
        Returns one of: flowchart | graph | table | identity_doc | other
        """
        try:
            image_b64, _ = _load_and_resize(file_path)
            prompt = (
                "Look at this image and classify it into exactly ONE category.\n"
                "Reply with ONLY one word from this list:\n"
                "- flowchart  (process flow, decision tree, workflow diagram, org chart)\n"
                "- graph      (bar chart, line chart, pie chart, scatter plot, histogram)\n"
                "- table      (data table, spreadsheet screenshot, financial statement)\n"
                "- identity_doc  (Aadhaar, PAN card, passport, driving licence, bank statement)\n"
                "- other      (anything else: photo, screenshot, map, etc.)\n\n"
                "Reply with ONE word only. No explanation."
            )
            raw = self._call(image_b64, prompt, max_tokens=10).strip().lower()
            if raw in {"flowchart", "graph", "table", "identity_doc", "other"}:
                logger.info(f"Image category detected: {raw} for {file_path.name}")
                return raw
            return "other"
        except Exception as exc:
            logger.warning(f"Image category detection failed: {exc}")
            return "other"

    # ------------------------------------------------------------------
    # Public: PDF chart / graph description
    # ------------------------------------------------------------------

    # Type-specific prompts for different image categories
    _PROMPTS = {
        "flowchart": (
            "You are analysing a flowchart or process diagram.\n\n"
            "Describe it EXHAUSTIVELY in plain text. Follow STRICTLY:\n"
            "1. State the EXACT text and SHAPE of the starting node (parallelogram = input/trigger, oval = start/end).\n"
            "2. Count ALL decision diamonds — number them 1, 2, 3... with EXACT label text from the image.\n"
            "3. For EACH decision: state BOTH Yes path destination AND No path destination with exact text.\n"
            "4. Trace the COMPLETE flow in strict top-to-bottom order — do NOT skip any intermediate steps.\n"
            "5. State the EXACT text and shape of all end/terminal nodes.\n"
            "6. Note the COLOR of each shape type (e.g. 'process boxes are blue', 'decision diamonds are green', 'end node is pink/red rounded rectangle').\n"
            "7. Note GEOMETRIC SHAPE of each node type.\n"
            "Use numbered steps. Include exact quoted text for every node. Do NOT output JSON. Max 1000 words."
        ),
        "graph": (
            "You are analysing a chart or graph.\n\n"
            "Describe it EXHAUSTIVELY in plain text:\n"
            "1. Chart type (bar, line, pie, scatter, histogram, etc.).\n"
            "2. Title of the chart (exact text).\n"
            "3. X-axis label and range of values.\n"
            "4. Y-axis label and range of values.\n"
            "5. All data series / legend labels with their colors.\n"
            "6. Key data points, peaks, troughs — include EXACT numbers.\n"
            "7. Overall trend or insight the chart shows.\n"
            "8. Any annotations, callouts, or highlighted values.\n"
            "Write in clear prose. Do NOT output JSON. Max 600 words."
        ),
        "table": (
            "You are analysing a data table or financial statement.\n\n"
            "Describe it EXHAUSTIVELY in plain text:\n"
            "1. Table title or heading (exact text).\n"
            "2. All column headers in order (exact text).\n"
            "3. Number of rows.\n"
            "4. First 10 rows of data with all column values.\n"
            "5. Any totals, subtotals, or summary rows.\n"
            "6. Any highlighted, bold, or specially formatted cells and what they contain.\n"
            "7. Any footnotes or legends below the table.\n"
            "Write in clear prose. Do NOT output JSON. Max 600 words."
        ),
        "other": (
            "You are analysing a business image or document screenshot.\n\n"
            "Describe ALL visible content in plain text:\n"
            "1. What type of document or image this appears to be.\n"
            "2. All text visible in the image — read it carefully and quote exactly.\n"
            "3. Any diagrams, icons, logos, or visual elements and what they show.\n"
            "4. Layout and structure of the content.\n"
            "5. Any numbers, dates, names, or key data points visible.\n"
            "Write in clear prose. Do NOT output JSON. Max 600 words."
        ),
    }

    def analyze_chart(self, file_path: Path, page_num: int = 0, image_category: str = None) -> str:
        """
        Analyse an image with a type-specific prompt for maximum accuracy.
        - flowchart: exhaustive node/decision/color/shape description
        - graph: axes, data points, trends
        - table: headers, rows, values
        - other: general content extraction
        Returns plain-text description for RAG indexing.
        """
        try:
            image_b64, _ = _load_and_resize(file_path)

            # Use provided category or fall back to "other"
            category = image_category if image_category in self._PROMPTS else "other"
            prompt = self._PROMPTS[category]
            logger.info(f"analyze_chart using prompt type: {category} for {file_path.name}")

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

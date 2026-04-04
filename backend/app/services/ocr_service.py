"""
OCR Service — Tesseract-based text extraction from preprocessed images.

Tesseract is OPTIONAL: if it is not installed on the host system, all extract()
calls return an empty result instead of crashing. A warning is logged once at
startup so the developer knows OCR is unavailable.
"""

import logging
from typing import Dict, Any, List

from PIL import Image

logger = logging.getLogger(__name__)

# ── Tesseract availability check (done once at import time) ──────────────────
_TESSERACT_AVAILABLE = False
_TESSERACT_WARNED = False

try:
    import pytesseract
    # Quick smoke-test: asking for the version is cheaper than running OCR
    pytesseract.get_tesseract_version()
    _TESSERACT_AVAILABLE = True
except Exception:
    pass  # Logged lazily on first extract() call


class OCRService:
    """
    Tesseract-based OCR layer.

    Returns:
      ocr_text             — extracted text string
      ocr_rows             — per-word data (may be empty list if tesseract absent)
      ocr_avg_confidence   — average confidence (0.0 if tesseract absent)
      ocr_variant_used     — 'binary' | 'grayscale' | 'unavailable'
    """

    def _warn_once(self):
        global _TESSERACT_WARNED
        if not _TESSERACT_WARNED:
            logger.warning(
                "Tesseract OCR is not installed or not in PATH — "
                "OCR extraction is disabled. "
                "Install: https://github.com/tesseract-ocr/tesseract#installing-tesseract"
            )
            _TESSERACT_WARNED = True

    def _extract_data_rows(self, img: Image.Image) -> List[dict]:
        data = pytesseract.image_to_data(
            img,
            output_type=pytesseract.Output.DICT,
            config="--oem 3 --psm 6",
        )

        rows = []
        n = len(data.get("text", []))
        for i in range(n):
            text = (data["text"][i] or "").strip()
            conf = data["conf"][i]
            if not text:
                continue

            try:
                conf_val = float(conf)
            except Exception:
                conf_val = -1.0

            rows.append({
                "text": text,
                "confidence": conf_val,
                "left": int(data["left"][i]),
                "top": int(data["top"][i]),
                "width": int(data["width"][i]),
                "height": int(data["height"][i]),
                "line_num": int(data["line_num"][i]),
                "block_num": int(data["block_num"][i]),
            })

        return rows

    def _avg_confidence(self, rows: List[dict]) -> float:
        vals = [r["confidence"] for r in rows if r["confidence"] >= 0]
        if not vals:
            return 0.0
        return round(sum(vals) / len(vals), 2)

    def extract(self, grayscale_img: Image.Image, binary_img: Image.Image) -> Dict[str, Any]:
        """
        Run OCR on grayscale + binary variants.
        Returns safe empty result if tesseract is not available.
        """
        if not _TESSERACT_AVAILABLE:
            self._warn_once()
            return {
                "ocr_text": "",
                "ocr_rows": [],
                "ocr_avg_confidence": 0.0,
                "ocr_variant_used": "unavailable",
            }

        try:
            # Try binary first (stronger contrast → better OCR)
            text_binary = pytesseract.image_to_string(binary_img, config="--oem 3 --psm 6")
            rows_binary = self._extract_data_rows(binary_img)
            conf_binary = self._avg_confidence(rows_binary)

            # Grayscale for comparison
            text_gray = pytesseract.image_to_string(grayscale_img, config="--oem 3 --psm 6")
            rows_gray = self._extract_data_rows(grayscale_img)
            conf_gray = self._avg_confidence(rows_gray)

            if conf_binary >= conf_gray:
                return {
                    "ocr_text": text_binary.strip(),
                    "ocr_rows": rows_binary,
                    "ocr_avg_confidence": conf_binary,
                    "ocr_variant_used": "binary",
                }
            else:
                return {
                    "ocr_text": text_gray.strip(),
                    "ocr_rows": rows_gray,
                    "ocr_avg_confidence": conf_gray,
                    "ocr_variant_used": "grayscale",
                }

        except Exception as exc:
            logger.warning(f"OCR extraction failed: {exc}")
            return {
                "ocr_text": "",
                "ocr_rows": [],
                "ocr_avg_confidence": 0.0,
                "ocr_variant_used": "error",
            }


ocr_service = OCRService()

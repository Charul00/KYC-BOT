import json
from typing import Dict, Any


class ImageMergeService:
    """
    Merge strategy:
    - vision primary
    - OCR gap-fill
    - highest confidence wins per field
    """

    def _field_text_from_ocr(self, ocr_text: str, field_name: str) -> str:
        # lightweight placeholder; later can improve with regexes
        return ""

    def merge(self, quality: Dict[str, Any], ocr_result: Dict[str, Any], vision_result: Dict[str, Any]) -> Dict[str, Any]:
        merged_fields = {}

        vision_fields = vision_result.get("fields", {}) or {}
        ocr_text = ocr_result.get("ocr_text", "")

        for field_name, info in vision_fields.items():
            value = info.get("value", "") if isinstance(info, dict) else ""
            confidence = float(info.get("confidence", 0.0)) if isinstance(info, dict) else 0.0

            if value:
                merged_fields[field_name] = {
                    "value": value,
                    "confidence": confidence,
                    "source": "vision",
                }
            else:
                ocr_guess = self._field_text_from_ocr(ocr_text, field_name)
                merged_fields[field_name] = {
                    "value": ocr_guess,
                    "confidence": min(0.6, float(ocr_result.get("ocr_avg_confidence", 0.0)) / 100.0),
                    "source": "ocr" if ocr_guess else "none",
                }

        full_text_parts = [
            f"Document type: {vision_result.get('doc_type', 'unknown')}",
            f"Summary: {vision_result.get('document_summary', '')}",
            "",
            "OCR text:",
            ocr_text,
            "",
            "Structured fields:",
            json.dumps(merged_fields, ensure_ascii=False, indent=2),
        ]

        if vision_result.get("process_rules_detected"):
            full_text_parts.extend([
                "",
                "Process rules detected:",
                "\n".join(f"- {x}" for x in vision_result.get("process_rules_detected", []))
            ])

        if vision_result.get("risk_terms_detected"):
            full_text_parts.extend([
                "",
                "Risk terms detected:",
                "\n".join(f"- {x}" for x in vision_result.get("risk_terms_detected", []))
            ])

        return {
            "doc_type": vision_result.get("doc_type", "unknown"),
            "document_summary": vision_result.get("document_summary", ""),
            "fields": merged_fields,
            "tables": vision_result.get("tables", []),
            "face_present": bool(vision_result.get("face_present", False)),
            "overall_confidence": float(vision_result.get("overall_confidence", 0.0)),
            "quality": quality,
            "ocr_avg_confidence": ocr_result.get("ocr_avg_confidence", 0.0),
            "risk_terms_detected": vision_result.get("risk_terms_detected", []),
            "process_rules_detected": vision_result.get("process_rules_detected", []),
            "merged_text": "\n".join(full_text_parts).strip(),
        }


image_merge_service = ImageMergeService()
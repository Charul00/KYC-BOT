import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, List

from pptx import Presentation

from app.services.image_preprocessor import image_preprocessor
from app.services.ocr_service import ocr_service
from app.services.vision_service import vision_service
from app.services.image_merge_service import image_merge_service

logger = logging.getLogger(__name__)


class PPTService:
    """
    Handles PPT/PPTX extraction:
    - slide text
    - notes text
    - embedded images -> image pipeline
    """

    def _extract_slide_text(self, slide) -> str:
        parts = []

        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                parts.append(shape.text.strip())

            # Tables
            if getattr(shape, "has_table", False):
                table = shape.table
                for row in table.rows:
                    row_vals = []
                    for cell in row.cells:
                        txt = (cell.text or "").strip()
                        if txt:
                            row_vals.append(txt)
                    if row_vals:
                        parts.append(" | ".join(row_vals))

        return "\n".join(p for p in parts if p)

    def _extract_notes_text(self, slide) -> str:
        try:
            if not slide.has_notes_slide:
                return ""
            notes_slide = slide.notes_slide
            parts = []
            for shape in notes_slide.shapes:
                if hasattr(shape, "text") and shape.text:
                    parts.append(shape.text.strip())
            return "\n".join(p for p in parts if p)
        except Exception as e:
            logger.warning(f"Failed to extract notes text: {e}")
            return ""

    def _extract_slide_images_text(self, slide) -> List[str]:
        """
        Extract embedded images from slide and run image pipeline on each.
        """
        image_texts: List[str] = []

        for idx, shape in enumerate(slide.shapes):
            try:
                if shape.shape_type == 13:  # PICTURE
                    image = shape.image
                    ext = image.ext.lower()
                    if ext == "jpg":
                        ext = "jpeg"

                    suffix = f".{ext}"
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                        tmp.write(image.blob)
                        tmp_path = Path(tmp.name)

                    try:
                        bundle = image_preprocessor.preprocess(tmp_path)
                        ocr_result = ocr_service.extract(bundle.grayscale_image, bundle.binary_image)
                        vision_result = vision_service.analyze(tmp_path)
                        merged = image_merge_service.merge(bundle.quality, ocr_result, vision_result)

                        image_texts.append(
                            f"[Slide embedded image {idx + 1}]\n{merged['merged_text']}"
                        )
                    finally:
                        try:
                            tmp_path.unlink(missing_ok=True)
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"Failed to process slide image {idx + 1}: {e}")

        return image_texts

    def extract_text_and_metadata(self, file_path: Path):
        prs = Presentation(str(file_path))

        all_parts = []
        metadata: Dict[str, Any] = {
            "ppt_pipeline": True,
            "slide_count": len(prs.slides),
        }

        for slide_idx, slide in enumerate(prs.slides, start=1):
            slide_parts = [f"[Slide {slide_idx}]"]

            slide_text = self._extract_slide_text(slide)
            if slide_text:
                slide_parts.append("Slide text:")
                slide_parts.append(slide_text)

            notes_text = self._extract_notes_text(slide)
            if notes_text:
                slide_parts.append("Slide notes:")
                slide_parts.append(notes_text)

            image_texts = self._extract_slide_images_text(slide)
            if image_texts:
                slide_parts.append("Embedded image analysis:")
                slide_parts.extend(image_texts)

            all_parts.append("\n".join(slide_parts))

        return "\n\n".join(all_parts).strip(), metadata


ppt_service = PPTService()
import base64
import logging
from pathlib import Path

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class ImageService:
    """
    Handles image-based document understanding using a multimodal model.
    Supports JPG / JPEG / PNG.

    Output is text that can be indexed into RAG.
    """

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def _guess_mime_type(self, file_path: Path) -> str:
        ext = file_path.suffix.lower()
        if ext == ".png":
            return "image/png"
        if ext in [".jpg", ".jpeg"]:
            return "image/jpeg"
        return "application/octet-stream"

    def _encode_image(self, file_path: Path) -> str:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def extract_text(self, file_path: Path) -> str:
        """
        Extract image text + semantic document understanding.

        The result is intentionally verbose enough to support:
        - OCR-like extraction
        - field understanding
        - later RAG retrieval
        """
        try:
            mime_type = self._guess_mime_type(file_path)
            b64 = self._encode_image(file_path)

            prompt = """
You are an OCR + document understanding assistant for KYC workflows.

Analyze this image carefully and return plain text only.

Your output must contain:
1. A short description of what this image appears to be.
2. All readable text visible in the image.
3. Any structured fields you can identify, such as:
   - customer name
   - ID number
   - address
   - date of birth
   - document type
   - issue date / expiry date
   - risk-related terms
4. If the image appears to be a process/BRD/policy screenshot, summarize the rules or guidance visible.
5. If the image is unclear, say what is unclear.

Do not return JSON.
Do not use markdown tables.
Return only the extracted and interpreted text.
"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.0,
                max_tokens=1800,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{b64}"
                                },
                            },
                        ],
                    }
                ],
            )

            text = response.choices[0].message.content or ""
            return text.strip()

        except Exception as e:
            logger.error(f"Image extraction failed for {file_path.name}: {e}")
            raise


image_service = ImageService()
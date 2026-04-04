import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageStat

logger = logging.getLogger(__name__)


@dataclass
class PreprocessedImageBundle:
    original_image: Image.Image
    enhanced_image: Image.Image
    grayscale_image: Image.Image
    binary_image: Image.Image
    quality: Dict[str, float]


class ImagePreprocessor:
    """
    Preprocesses images for OCR + vision.
    Steps:
    - EXIF transpose
    - RGB normalize
    - resize shorter side to min 800 px
    - contrast enhance
    - sharpen
    - grayscale + binarized OCR variants
    - compute lightweight quality metrics
    """

    def _load_image(self, file_path: Path) -> Image.Image:
        img = Image.open(file_path)
        img = ImageOps.exif_transpose(img)
        return img.convert("RGB")

    def _resize_min_side(self, img: Image.Image, min_side: int = 800) -> Image.Image:
        w, h = img.size
        current_min = min(w, h)
        if current_min >= min_side:
            return img

        scale = min_side / float(current_min)
        new_size = (int(w * scale), int(h * scale))
        return img.resize(new_size, Image.LANCZOS)

    def _enhance(self, img: Image.Image) -> Image.Image:
        enhanced = ImageEnhance.Contrast(img).enhance(1.25)
        enhanced = ImageEnhance.Sharpness(enhanced).enhance(1.6)
        enhanced = ImageEnhance.Brightness(enhanced).enhance(1.02)
        return enhanced

    def _to_grayscale(self, img: Image.Image) -> Image.Image:
        return ImageOps.grayscale(img)

    def _to_binary(self, gray: Image.Image) -> Image.Image:
        # simple threshold
        return gray.point(lambda p: 255 if p > 160 else 0)

    def _estimate_blur(self, gray: Image.Image) -> float:
        # lightweight blur proxy using edge variation after FIND_EDGES
        edges = gray.filter(ImageFilter.FIND_EDGES)
        stat = ImageStat.Stat(edges)
        return float(stat.stddev[0])

    def _quality_score(self, gray: Image.Image, original: Image.Image) -> Dict[str, float]:
        stat = ImageStat.Stat(gray)
        brightness = float(stat.mean[0])
        stddev = float(stat.stddev[0])
        blur_proxy = self._estimate_blur(gray)
        width, height = original.size

        readable = 1.0
        if brightness < 40 or brightness > 230:
            readable -= 0.25
        if stddev < 25:
            readable -= 0.25
        if blur_proxy < 15:
            readable -= 0.25
        if min(width, height) < 600:
            readable -= 0.15

        readable = max(0.0, min(1.0, readable))

        return {
            "brightness": round(brightness, 2),
            "stddev": round(stddev, 2),
            "blur_proxy": round(blur_proxy, 2),
            "width": float(width),
            "height": float(height),
            "readability_score": round(readable, 2),
        }

    def preprocess(self, file_path: Path) -> PreprocessedImageBundle:
        original = self._load_image(file_path)
        resized = self._resize_min_side(original, min_side=800)
        enhanced = self._enhance(resized)
        gray = self._to_grayscale(enhanced)
        binary = self._to_binary(gray)
        quality = self._quality_score(gray, enhanced)

        logger.info(
            f"Image preprocessed: {file_path.name} | "
            f"readability={quality['readability_score']} | "
            f"brightness={quality['brightness']} | stddev={quality['stddev']}"
        )

        return PreprocessedImageBundle(
            original_image=original,
            enhanced_image=enhanced,
            grayscale_image=gray,
            binary_image=binary,
            quality=quality,
        )

    def image_to_bytes(self, img: Image.Image, format: str = "PNG") -> bytes:
        buf = io.BytesIO()
        img.save(buf, format=format)
        return buf.getvalue()


image_preprocessor = ImagePreprocessor()
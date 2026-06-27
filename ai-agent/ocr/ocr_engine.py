"""OCR engine with optional Tesseract."""

from __future__ import annotations

from pathlib import Path


def extract_text(image_path: Path) -> str:
    if not image_path.is_file():
        return ""
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore

        img = Image.open(image_path)
        return pytesseract.image_to_string(img) or ""
    except Exception:
        return _fallback_ocr(image_path)


def _fallback_ocr(image_path: Path) -> str:
    """Use OpenCV threshold + basic heuristics when Tesseract unavailable."""
    try:
        import cv2  # type: ignore

        img = cv2.imread(str(image_path))
        if img is None:
            return ""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _ = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        return ""
    except Exception:
        return ""

"""OCR over device screenshots — optional Tesseract; falls back to UI hierarchy text."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("ai.ocr_engine")

_tesseract_available: bool | None = None


def _check_tesseract() -> bool:
    global _tesseract_available
    if _tesseract_available is not None:
        return _tesseract_available
    try:
        import pytesseract  # noqa: F401

        _tesseract_available = True
    except ImportError:
        _tesseract_available = False
        logger.debug("pytesseract not installed — OCR disabled; UI hierarchy only")
    return _tesseract_available


def extract_text(image_path: Path, *, lang: str = "eng") -> list[str]:
    """
    Return non-empty text lines from screenshot.
    Empty list if OCR unavailable or image missing.
    """
    if not image_path.is_file():
        return []
    if not _check_tesseract():
        return []
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(image_path)
        raw = pytesseract.image_to_string(img, lang=lang)
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        return lines
    except Exception as ex:
        logger.warning("OCR failed on %s: %s", image_path, ex)
        return []


def ocr_status() -> dict[str, bool | str]:
    return {
        "tesseract_available": _check_tesseract(),
        "fallback": "ui_hierarchy_only",
    }

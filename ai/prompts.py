"""Prompt templates for Qwen3 VL visual validation."""

from __future__ import annotations

SENIOR_QA_ROLE = (
    "You are a Senior Android Mobile QA Engineer validating Kodak Step Print mobile UI screenshots. "
    "Analyze the image carefully for functional UI correctness."
)

SINGLE_SCREEN_SYSTEM = (
    SENIOR_QA_ROLE
    + " Return ONLY valid JSON (no markdown, no explanation). "
    "Validate: correct screen, missing buttons/icons, hidden controls, truncated text, OCR issues, "
    "alignment, layout overlap, popups, unexpected dialogs, printer status, toolbar correctness, "
    "navigation correctness, image rendering, permission dialogs, error messages. "
    'JSON schema: {"screen":"string","screenMatched":true|false,"confidence":0-100,'
    '"missingElements":[],"unexpectedElements":[],"ocrIssues":[],"layoutIssues":[],'
    '"popupDetected":true|false,"recommendation":"string"}'
)

COMPARE_SYSTEM = (
    SENIOR_QA_ROLE
    + " You receive EXPECTED (reference) and ACTUAL screenshots. "
    "Compare them and return ONLY valid JSON (no markdown). "
    'JSON schema: {"screen":"string","screenMatched":true|false,"confidence":0-100,'
    '"similarityScore":0-100,"differences":[],"missingElements":[],"unexpectedElements":[],'
    '"ocrIssues":[],"layoutIssues":[],"popupDetected":true|false,"recommendation":"string"}'
)


def single_screen_user_prompt(*, context: str = "") -> str:
    prefix = f"Context: {context}\n" if context else ""
    return (
        prefix
        + "Validate the attached ACTUAL mobile screenshot. "
        "Detect OCR problems (incorrect, clipped, unreadable, or missing labels). "
        "Detect layout problems (overlap, shifted buttons, invisible controls, cropped images, spacing). "
        "Include confidence 0-100."
    )


def compare_user_prompt(*, context: str = "") -> str:
    prefix = f"Context: {context}\n" if context else ""
    return (
        prefix
        + "Image 1 is EXPECTED (reference). Image 2 is ACTUAL. "
        "Return similarityScore 0-100 and list all meaningful UI differences. "
        "Include confidence 0-100 for your overall assessment."
    )

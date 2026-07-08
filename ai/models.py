"""Data models for AI visual validation (isolated from Maestro automation)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ValidationMode(str, Enum):
    SINGLE = "single"
    COMPARE = "compare"


class ValidationStatus(str, Enum):
    OK = "OK"
    AI_SKIPPED = "AI_SKIPPED"


@dataclass(frozen=True)
class VisualValidationConfig:
    """Runtime configuration (env + optional YAML)."""

    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "meta-llama/llama-3.2-11b-vision-instruct:free"
    fallback_models: tuple[str, ...] = ()
    timeout_sec: float = 60.0
    max_retries: int = 3
    retry_backoff_sec: float = 2.0
    rate_limit_rps: float = 2.0
    http_referer: str = "http://localhost"
    app_title: str = "Kodak Visual Validation"
    ssl_verify: bool = True
    cache_dir: Path = field(default_factory=lambda: Path(".cache/ai_visual"))
    log_file: Path = field(default_factory=lambda: Path("logs/visual_validation.log"))
    max_concurrent: int = 2


@dataclass(frozen=True)
class ScreenshotRef:
    path: Path
    label: str = ""
    sha256: str = ""


@dataclass
class VisualValidationResult:
    """Structured validation output (success or AI_SKIPPED)."""

    status: str = ValidationStatus.OK.value
    screen: str = ""
    screen_matched: bool = False
    confidence: int = 0
    missing_elements: list[str] = field(default_factory=list)
    unexpected_elements: list[str] = field(default_factory=list)
    ocr_issues: list[str] = field(default_factory=list)
    layout_issues: list[str] = field(default_factory=list)
    popup_detected: bool = False
    recommendation: str = ""
    # Compare mode extras
    similarity_score: int | None = None
    differences: list[str] = field(default_factory=list)
    # Metadata (not part of core contract but useful for merge)
    model_used: str = ""
    execution_ms: int = 0
    retry_count: int = 0
    token_usage: dict[str, int] = field(default_factory=dict)
    screenshot_path: str = ""
    expected_screenshot_path: str = ""
    mode: str = ValidationMode.SINGLE.value
    testcase_id: str = ""
    error: str = ""

    def to_json_dict(self) -> dict[str, Any]:
        if self.status == ValidationStatus.AI_SKIPPED.value:
            out: dict[str, Any] = {"status": ValidationStatus.AI_SKIPPED.value}
            if self.error:
                out["error"] = self.error
            return out

        out = {
            "screen": self.screen,
            "screenMatched": self.screen_matched,
            "confidence": self.confidence,
            "missingElements": self.missing_elements,
            "unexpectedElements": self.unexpected_elements,
            "ocrIssues": self.ocr_issues,
            "layoutIssues": self.layout_issues,
            "popupDetected": self.popup_detected,
            "recommendation": self.recommendation,
        }
        if self.mode == ValidationMode.COMPARE.value:
            out["similarityScore"] = self.similarity_score
            out["differences"] = self.differences
        return out

    def to_report_dict(self) -> dict[str, Any]:
        """Full report payload including metadata for merge/debug."""
        base = self.to_json_dict()
        if self.status == ValidationStatus.AI_SKIPPED.value:
            return base
        base["_meta"] = {
            "modelUsed": self.model_used,
            "executionMs": self.execution_ms,
            "retryCount": self.retry_count,
            "tokenUsage": self.token_usage,
            "screenshotPath": self.screenshot_path,
            "expectedScreenshotPath": self.expected_screenshot_path,
            "mode": self.mode,
            "testcaseId": self.testcase_id,
        }
        return base


@dataclass
class ValidationJob:
    """One validation unit (single screenshot or pair)."""

    testcase_id: str
    mode: ValidationMode
    actual: ScreenshotRef
    expected: ScreenshotRef | None = None
    output_path: Path | None = None
    context: str = ""

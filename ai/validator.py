"""Core screenshot validation orchestration."""

from __future__ import annotations

import base64
import hashlib
import logging
import time
from pathlib import Path

from compare import parse_validation_response
from models import (
    ScreenshotRef,
    ValidationJob,
    ValidationMode,
    ValidationStatus,
    VisualValidationConfig,
    VisualValidationResult,
)
from openrouter_client import OpenRouterVisionClient
from prompts import COMPARE_SYSTEM, SINGLE_SCREEN_SYSTEM, compare_user_prompt, single_screen_user_prompt

logger = logging.getLogger("visual_validation.validator")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def encode_image_part(path: Path) -> dict:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}


class VisualValidator:
    def __init__(self, config: VisualValidationConfig, client: OpenRouterVisionClient | None = None) -> None:
        self._config = config
        self._client = client or OpenRouterVisionClient(config)

    def validate_job(
        self,
        job: ValidationJob,
        *,
        cache: dict[str, VisualValidationResult] | None = None,
        disk_cache_dir: Path | None = None,
    ) -> VisualValidationResult:
        started = time.perf_counter()
        cache = cache if cache is not None else {}

        if not job.actual.path.is_file():
            return self._skipped(f"screenshot not found: {job.actual.path}", job)

        actual_hash = job.actual.sha256 or sha256_file(job.actual.path)
        cache_key = self._cache_key(job, actual_hash)

        disk_hit = self._load_disk_cache(disk_cache_dir, cache_key) if disk_cache_dir else None
        if disk_hit is not None:
            logger.info("Disk cache hit testcase=%s key=%s", job.testcase_id, cache_key[:16])
            cache[cache_key] = disk_hit
            return self._clone_for_job(disk_hit, job, execution_ms=0)

        if cache_key in cache:
            logger.info("Cache hit testcase=%s key=%s", job.testcase_id, cache_key[:16])
            return self._clone_for_job(cache[cache_key], job, execution_ms=0)

        try:
            if job.mode == ValidationMode.COMPARE:
                if not job.expected or not job.expected.path.is_file():
                    return self._skipped("expected screenshot missing for compare mode", job)
                raw, model_used, token_usage, retries = self._call_compare(job)
            else:
                raw, model_used, token_usage, retries = self._call_single(job)

            result = parse_validation_response(raw, mode=job.mode)
            result.model_used = model_used
            result.token_usage = token_usage
            result.retry_count = retries
            result.screenshot_path = str(job.actual.path)
            if job.expected:
                result.expected_screenshot_path = str(job.expected.path)
            result.testcase_id = job.testcase_id
            result.mode = job.mode.value
            result.execution_ms = int((time.perf_counter() - started) * 1000)
            cache[cache_key] = result
            if disk_cache_dir is not None and result.status != ValidationStatus.AI_SKIPPED.value:
                self._save_disk_cache(disk_cache_dir, cache_key, result)
            return result
        except Exception as exc:
            logger.exception("Validation failed testcase=%s: %s", job.testcase_id, exc)
            return self._skipped(str(exc), job, execution_ms=int((time.perf_counter() - started) * 1000))

    def _call_single(self, job: ValidationJob) -> tuple[str, str, dict[str, int], int]:
        messages = [
            {"role": "system", "content": SINGLE_SCREEN_SYSTEM},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": single_screen_user_prompt(context=job.context)},
                    encode_image_part(job.actual.path),
                ],
            },
        ]
        logger.info("AI request mode=single testcase=%s screenshot=%s", job.testcase_id, job.actual.path.name)
        content, model_used, token_usage, retries = self._client.chat_completions(messages)
        logger.info(
            "AI response testcase=%s model=%s tokens=%s retries=%s",
            job.testcase_id,
            model_used,
            token_usage.get("total_tokens"),
            retries,
        )
        return content, model_used, token_usage, retries

    def _call_compare(self, job: ValidationJob) -> tuple[str, str, dict[str, int], int]:
        assert job.expected is not None
        messages = [
            {"role": "system", "content": COMPARE_SYSTEM},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": compare_user_prompt(context=job.context)},
                    {"type": "text", "text": "EXPECTED:"},
                    encode_image_part(job.expected.path),
                    {"type": "text", "text": "ACTUAL:"},
                    encode_image_part(job.actual.path),
                ],
            },
        ]
        logger.info(
            "AI request mode=compare testcase=%s expected=%s actual=%s",
            job.testcase_id,
            job.expected.path.name,
            job.actual.path.name,
        )
        content, model_used, token_usage, retries = self._client.chat_completions(messages, max_tokens=1000)
        logger.info(
            "AI response testcase=%s model=%s tokens=%s retries=%s",
            job.testcase_id,
            model_used,
            token_usage.get("total_tokens"),
            retries,
        )
        return content, model_used, token_usage, retries

    @staticmethod
    def _clone_for_job(cached: VisualValidationResult, job: ValidationJob, *, execution_ms: int) -> VisualValidationResult:
        return VisualValidationResult(
            status=cached.status,
            screen=cached.screen,
            screen_matched=cached.screen_matched,
            confidence=cached.confidence,
            missing_elements=list(cached.missing_elements),
            unexpected_elements=list(cached.unexpected_elements),
            ocr_issues=list(cached.ocr_issues),
            layout_issues=list(cached.layout_issues),
            popup_detected=cached.popup_detected,
            recommendation=cached.recommendation,
            similarity_score=cached.similarity_score,
            differences=list(cached.differences),
            model_used=cached.model_used,
            execution_ms=execution_ms,
            retry_count=0,
            token_usage=dict(cached.token_usage),
            screenshot_path=str(job.actual.path),
            expected_screenshot_path=str(job.expected.path) if job.expected else "",
            mode=job.mode.value,
            testcase_id=job.testcase_id,
        )

    @staticmethod
    def _disk_cache_path(cache_dir: Path, cache_key: str) -> Path:
        safe = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
        return cache_dir / f"{safe}.json"

    @staticmethod
    def _load_disk_cache(cache_dir: Path, cache_key: str) -> VisualValidationResult | None:
        path = VisualValidator._disk_cache_path(cache_dir, cache_key)
        if not path.is_file():
            return None
        try:
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            return VisualValidationResult(
                status=str(data.get("status") or "OK"),
                screen=str(data.get("screen") or ""),
                screen_matched=bool(data.get("screen_matched")),
                confidence=int(data.get("confidence") or 0),
                missing_elements=list(data.get("missing_elements") or []),
                unexpected_elements=list(data.get("unexpected_elements") or []),
                ocr_issues=list(data.get("ocr_issues") or []),
                layout_issues=list(data.get("layout_issues") or []),
                popup_detected=bool(data.get("popup_detected")),
                recommendation=str(data.get("recommendation") or ""),
                similarity_score=data.get("similarity_score"),
                differences=list(data.get("differences") or []),
                model_used=str(data.get("model_used") or ""),
                retry_count=int(data.get("retry_count") or 0),
                token_usage=dict(data.get("token_usage") or {}),
                mode=str(data.get("mode") or "single"),
            )
        except Exception:
            return None

    @staticmethod
    def _save_disk_cache(cache_dir: Path, cache_key: str, result: VisualValidationResult) -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = VisualValidator._disk_cache_path(cache_dir, cache_key)
        import json

        payload = {
            "status": result.status,
            "screen": result.screen,
            "screen_matched": result.screen_matched,
            "confidence": result.confidence,
            "missing_elements": result.missing_elements,
            "unexpected_elements": result.unexpected_elements,
            "ocr_issues": result.ocr_issues,
            "layout_issues": result.layout_issues,
            "popup_detected": result.popup_detected,
            "recommendation": result.recommendation,
            "similarity_score": result.similarity_score,
            "differences": result.differences,
            "model_used": result.model_used,
            "retry_count": result.retry_count,
            "token_usage": result.token_usage,
            "mode": result.mode,
            "cache_key": cache_key,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _cache_key(job: ValidationJob, actual_hash: str) -> str:
        if job.mode == ValidationMode.COMPARE and job.expected:
            exp_hash = job.expected.sha256 or sha256_file(job.expected.path)
            return f"compare:{exp_hash}:{actual_hash}"
        return f"single:{actual_hash}"

    @staticmethod
    def _skipped(msg: str, job: ValidationJob, *, execution_ms: int = 0) -> VisualValidationResult:
        return VisualValidationResult(
            status=ValidationStatus.AI_SKIPPED.value,
            error=msg,
            screenshot_path=str(job.actual.path) if job.actual else "",
            expected_screenshot_path=str(job.expected.path) if job.expected else "",
            testcase_id=job.testcase_id,
            mode=job.mode.value,
            execution_ms=execution_ms,
        )

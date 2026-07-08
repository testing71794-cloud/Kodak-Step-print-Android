"""
AI Visual Validation — plug-and-play post-Maestro screenshot analysis.

Does NOT modify Maestro YAML, Jenkins, or existing orchestration.
Invoke after a flow completes:

  py -3 AI/visual_validation.py --status-file status/editing__ED_Q1__DEVICE.txt
  py -3 AI/visual_validation.py --artifact-dir reports/editing/maestro-debug/FLOW__DEVICE
  py -3 AI/visual_validation.py --screenshot path/to.png --testcase-id TC001

Environment:
  OPENROUTER_API_KEY          (required for AI; skips gracefully if missing)
  AI_VISUAL_MODEL             default: qwen/qwen3-vl-8b-instruct:free
  AI_VISUAL_ENABLED=1         gate (default on when key present)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

# Flat package: ensure AI/ directory is importable when run as script
_PKG_DIR = Path(__file__).resolve().parent
if str(_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_PKG_DIR))

from models import (  # noqa: E402
    ScreenshotRef,
    ValidationJob,
    ValidationMode,
    VisualValidationConfig,
    VisualValidationResult,
)
from openrouter_client import OpenRouterVisionClient  # noqa: E402
from report_formatter import default_output_path, merge_index_entry, write_validation_json  # noqa: E402
from validator import VisualValidator, sha256_file  # noqa: E402

REPO_ROOT = _PKG_DIR.parent


def load_dotenv_file(path: Path | None = None) -> None:
    """Load KEY=VALUE lines from repo .env without overriding existing env."""
    env_path = path or (REPO_ROOT / ".env")
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def _truthy(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _ssl_verify_enabled() -> bool:
    for name in ("OPENROUTER_SSL_VERIFY", "AI_VISUAL_SSL_VERIFY"):
        val = os.environ.get(name)
        if val is not None and val.strip().lower() in {"0", "false", "no", "off"}:
            return False
    return True


def _load_yaml_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        import yaml  # type: ignore
    except ImportError:
        # Minimal fallback parser for simple key: value lines
        out: dict[str, Any] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
        return out
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_config(config_path: Path | None = None) -> VisualValidationConfig:
    cfg_path = config_path or (_PKG_DIR / "config.yaml")
    yml = _load_yaml_config(cfg_path)

    def _env(name: str, default: str = "") -> str:
        return (os.environ.get(name) or "").strip() or str(yml.get(name.lower().replace("ai_visual_", ""), default) or default)

    api_key = (
        (os.environ.get("OPENROUTER_API_KEY") or "").strip()
        or (os.environ.get("OpenRouterAPI") or "").strip()
        or (os.environ.get("OPENROUTER_KEY") or "").strip()
    )

    model = (
        (os.environ.get("AI_VISUAL_MODEL") or "").strip()
        or str(yml.get("model") or "").strip()
        or "meta-llama/llama-3.2-11b-vision-instruct:free"
    )
    # Honor OPENROUTER_MODEL_VISION when set (shared with editing verify server).
    vision_env = (os.environ.get("OPENROUTER_MODEL_VISION") or "").strip()
    if vision_env and not (os.environ.get("AI_VISUAL_MODEL") or "").strip():
        model = vision_env

    fallbacks_raw = yml.get("fallback_models") or []
    if isinstance(fallbacks_raw, str):
        fallbacks = tuple(x.strip() for x in fallbacks_raw.split(",") if x.strip())
    else:
        fallbacks = tuple(str(x) for x in fallbacks_raw if str(x).strip())

    cache_dir = Path(_env("AI_VISUAL_CACHE_DIR") or str(yml.get("cache_dir") or ".cache/ai_visual"))
    if not cache_dir.is_absolute():
        cache_dir = REPO_ROOT / cache_dir

    log_file = Path(_env("AI_VISUAL_LOG_FILE") or str(yml.get("log_file") or "logs/visual_validation.log"))
    if not log_file.is_absolute():
        log_file = REPO_ROOT / log_file

    return VisualValidationConfig(
        api_key=api_key,
        base_url=(os.environ.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1").rstrip("/"),
        model=model,
        fallback_models=fallbacks,
        timeout_sec=float(_env("AI_VISUAL_TIMEOUT_SEC") or str(yml.get("timeout_sec") or 60)),
        max_retries=int(_env("AI_VISUAL_MAX_RETRIES") or str(yml.get("max_retries") or 3)),
        retry_backoff_sec=float(_env("AI_VISUAL_RETRY_BACKOFF_SEC") or str(yml.get("retry_backoff_sec") or 2)),
        rate_limit_rps=float(_env("AI_VISUAL_RATE_LIMIT_RPS") or str(yml.get("rate_limit_rps") or 2)),
        http_referer=(os.environ.get("OPENROUTER_HTTP_REFERER") or "http://localhost").strip(),
        app_title=(os.environ.get("OPENROUTER_APP_TITLE") or "Kodak Visual Validation").strip(),
        ssl_verify=_ssl_verify_enabled(),
        cache_dir=cache_dir,
        log_file=log_file,
        max_concurrent=int(_env("AI_VISUAL_MAX_CONCURRENT") or str(yml.get("max_concurrent") or 2)),
    )


def setup_logging(log_file: Path, verbose: bool = False) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    root = logging.getLogger("visual_validation")
    root.setLevel(level)
    root.handlers.clear()

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    sh.setLevel(level)
    root.addHandler(sh)


def parse_status_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.is_file():
        return data
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data


def discover_screenshots(artifact_dir: Path) -> list[Path]:
    if not artifact_dir.is_dir():
        return []
    pngs = [p for p in artifact_dir.rglob("*.png") if p.is_file()]
    pngs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return pngs


def discover_from_repo_roots(name_hint: str = "") -> list[Path]:
    """Reuse existing Maestro screenshot locations without changing them."""
    roots = [
        REPO_ROOT,
        REPO_ROOT / "reports",
        Path.home() / ".maestro" / "tests",
        Path.home() / ".maestro" / "screenshots",
    ]
    found: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        pattern = f"*{name_hint}*.png" if name_hint else "*.png"
        for p in root.rglob(pattern):
            if p.is_file():
                found.append(p)
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found


def build_jobs_for_artifact_dir(
    artifact_dir: Path,
    *,
    testcase_id: str,
    context: str,
    mode: ValidationMode,
    expected: Path | None,
) -> list[ValidationJob]:
    pngs = discover_screenshots(artifact_dir)
    if not pngs:
        return []

    jobs: list[ValidationJob] = []
    if mode == ValidationMode.COMPARE and expected and expected.is_file():
        actual = pngs[0]
        jobs.append(
            ValidationJob(
                testcase_id=testcase_id,
                mode=ValidationMode.COMPARE,
                actual=ScreenshotRef(path=actual, label="actual"),
                expected=ScreenshotRef(path=expected, label="expected"),
                output_path=default_output_path(actual, testcase_id),
                context=context,
            )
        )
        return jobs

    # Single mode: validate latest screenshot (primary testcase artifact)
    actual = pngs[0]
    jobs.append(
        ValidationJob(
            testcase_id=testcase_id,
            mode=ValidationMode.SINGLE,
            actual=ScreenshotRef(path=actual, label="actual"),
            output_path=default_output_path(actual, testcase_id),
            context=context,
        )
    )
    return jobs


class VisualValidationService:
    """High-level service with in-memory cache and optional thread-pool concurrency."""

    def __init__(self, config: VisualValidationConfig) -> None:
        self._config = config
        self._validator = VisualValidator(config)
        self._cache: dict[str, VisualValidationResult] = {}
        self._cache_dir = config.cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def validate_job(self, job: ValidationJob) -> VisualValidationResult:
        if not _truthy("AI_VISUAL_ENABLED", "1"):
            return VisualValidationResult(
                status="AI_SKIPPED",
                error="AI_VISUAL_ENABLED=0",
                testcase_id=job.testcase_id,
                screenshot_path=str(job.actual.path),
                mode=job.mode.value,
            )
        if not self._config.api_key:
            return VisualValidationResult(
                status="AI_SKIPPED",
                error="OPENROUTER_API_KEY not set",
                testcase_id=job.testcase_id,
                screenshot_path=str(job.actual.path),
                mode=job.mode.value,
            )
        return self._validator.validate_job(job, cache=self._cache, disk_cache_dir=self._cache_dir)

    def validate_jobs(self, jobs: list[ValidationJob]) -> list[VisualValidationResult]:
        if not jobs:
            return []
        if self._config.max_concurrent <= 1:
            return [self.validate_job(j) for j in jobs]

        results: list[VisualValidationResult] = []
        with ThreadPoolExecutor(max_workers=self._config.max_concurrent) as pool:
            futures = [pool.submit(self.validate_job, job) for job in jobs]
            for fut in futures:
                results.append(fut.result())
        return results

    async def validate_jobs_async(self, jobs: list[ValidationJob]) -> list[VisualValidationResult]:
        loop = asyncio.get_event_loop()
        if self._config.max_concurrent <= 1:
            return [await loop.run_in_executor(None, self.validate_job, j) for j in jobs]
        sem = asyncio.Semaphore(self._config.max_concurrent)

        async def _one(job: ValidationJob) -> VisualValidationResult:
            async with sem:
                return await loop.run_in_executor(None, self.validate_job, job)

        return await asyncio.gather(*[_one(j) for j in jobs])


def run_post_maestro(
    *,
    status_file: Path | None = None,
    artifact_dir: Path | None = None,
    screenshot: Path | None = None,
    expected: Path | None = None,
    testcase_id: str = "",
    context: str = "",
    mode: ValidationMode = ValidationMode.SINGLE,
    config_path: Path | None = None,
    verbose: bool = False,
) -> list[Path]:
    """
    Run visual validation and write visual_validation.json beside screenshot(s).
    Never raises — failures return AI_SKIPPED JSON.
    """
    load_dotenv_file()
    config = load_config(config_path)
    setup_logging(config.log_file, verbose=verbose)
    logger = logging.getLogger("visual_validation")

    if status_file and status_file.is_file():
        meta = parse_status_file(status_file)
        if not artifact_dir and meta.get("test_output_dir"):
            artifact_dir = Path(meta["test_output_dir"])
        if not testcase_id:
            flow = meta.get("flow", "")
            device = meta.get("device_id") or meta.get("device", "")
            testcase_id = f"{flow}__{device}" if flow else device
        if not context:
            context = f"suite={meta.get('suite','')} flow={meta.get('flow','')} status={meta.get('status','')}"

    jobs: list[ValidationJob] = []
    if screenshot and screenshot.is_file():
        jobs.append(
            ValidationJob(
                testcase_id=testcase_id or screenshot.stem,
                mode=ValidationMode.COMPARE if expected else ValidationMode.SINGLE,
                actual=ScreenshotRef(path=screenshot),
                expected=ScreenshotRef(path=expected) if expected else None,
                output_path=default_output_path(screenshot, testcase_id),
                context=context,
            )
        )
    elif artifact_dir:
        jobs = build_jobs_for_artifact_dir(
            artifact_dir,
            testcase_id=testcase_id or artifact_dir.name,
            context=context,
            mode=mode,
            expected=expected,
        )
    else:
        logger.warning("No artifact_dir or screenshot provided — nothing to validate")
        return []

    service = VisualValidationService(config)
    started = time.perf_counter()
    results = service.validate_jobs(jobs)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info("Validated %s job(s) in %sms", len(results), elapsed_ms)

    written: list[Path] = []
    index_path = (artifact_dir or REPO_ROOT / "build-summary") / "visual_validation_index.jsonl"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    for job, result in zip(jobs, results):
        out = job.output_path or default_output_path(job.actual.path, job.testcase_id)
        write_validation_json(result, out)
        written.append(out)
        logger.info("Wrote %s status=%s", out, result.status)
        with index_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(merge_index_entry(result, job.actual.path), ensure_ascii=False) + "\n")

    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Post-Maestro AI visual validation (Qwen3 VL)")
    parser.add_argument("--status-file", type=Path, help="status/*.txt from run_one_flow_on_device.bat")
    parser.add_argument("--artifact-dir", type=Path, help="Maestro debug output directory")
    parser.add_argument("--screenshot", type=Path, help="Single screenshot PNG")
    parser.add_argument("--expected", type=Path, help="Expected/reference PNG (compare mode)")
    parser.add_argument("--testcase-id", default="", help="Testcase identifier for report naming")
    parser.add_argument("--context", default="", help="Extra context for the model")
    parser.add_argument("--mode", choices=["single", "compare"], default="single")
    parser.add_argument("--config", type=Path, help="Path to config.yaml")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    mode = ValidationMode.COMPARE if args.mode == "compare" or args.expected else ValidationMode.SINGLE
    written = run_post_maestro(
        status_file=args.status_file,
        artifact_dir=args.artifact_dir,
        screenshot=args.screenshot,
        expected=args.expected,
        testcase_id=args.testcase_id,
        context=args.context,
        mode=mode,
        config_path=args.config,
        verbose=args.verbose,
    )
    if not written:
        return 0  # graceful: no screenshots is not a failure
    return 0  # never fail testcase / Jenkins


if __name__ == "__main__":
    raise SystemExit(main())

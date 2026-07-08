"""OpenRouter vision client for AI visual validation (isolated module)."""

from __future__ import annotations

import json
import logging
import ssl
import time
import urllib.error
import urllib.request
from typing import Any

from models import VisualValidationConfig

logger = logging.getLogger("visual_validation.openrouter")


class OpenRouterHTTPError(RuntimeError):
    def __init__(self, message: str, *, code: int | None = None, body: str = ""):
        super().__init__(message)
        self.code = code
        self.body = body


class RateLimiter:
    """Simple token-bucket style spacing between requests."""

    def __init__(self, requests_per_second: float) -> None:
        self._min_interval = 1.0 / requests_per_second if requests_per_second > 0 else 0.0
        self._last_at = 0.0

    def wait(self) -> None:
        if self._min_interval <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_at
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_at = time.monotonic()


class OpenRouterVisionClient:
    """HTTP client with session reuse, retries, timeout, and rate limiting."""

    def __init__(self, config: VisualValidationConfig) -> None:
        self._config = config
        self._rate_limiter = RateLimiter(config.rate_limit_rps)
        self._ssl_context = self._build_ssl_context()
        self._opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=self._ssl_context))

    def _build_ssl_context(self) -> ssl.SSLContext:
        if self._config.ssl_verify:
            return ssl.create_default_context()
        return ssl._create_unverified_context()

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.api_key}",
            "HTTP-Referer": self._config.http_referer,
            "X-Title": self._config.app_title,
        }

    def chat_completions(
        self,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int = 800,
    ) -> tuple[str, str, dict[str, int], int]:
        """
        Call OpenRouter chat/completions.
        Returns (content, model_used, token_usage, retry_count).
        """
        url = f"{self._config.base_url.rstrip('/')}/chat/completions"
        candidates = [self._config.model, *self._config.fallback_models]
        seen: set[str] = set()
        models: list[str] = []
        for m in candidates:
            if m and m not in seen:
                seen.add(m)
                models.append(m)

        last_error: Exception | None = None
        total_retries = 0

        for idx, model in enumerate(models):
            if idx > 0:
                logger.info("OpenRouter vision fallback: trying model=%s", model)
            for attempt in range(self._config.max_retries + 1):
                if attempt > 0:
                    total_retries += 1
                    backoff = self._config.retry_backoff_sec * attempt
                    logger.warning("Retry %s for model=%s after %.1fs", attempt, model, backoff)
                    time.sleep(backoff)

                self._rate_limiter.wait()
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": max_tokens,
                }
                body = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=body, headers=self._headers(), method="POST")

                try:
                    with self._opener.open(req, timeout=self._config.timeout_sec) as resp:
                        raw = resp.read().decode("utf-8", errors="replace")
                except urllib.error.HTTPError as exc:
                    err_body = ""
                    try:
                        err_body = exc.read().decode("utf-8", errors="replace")[:2000]
                    except Exception:
                        pass
                    last_error = OpenRouterHTTPError(
                        f"OpenRouter HTTP {exc.code}: {err_body or exc.reason}",
                        code=exc.code,
                        body=err_body,
                    )
                    if exc.code in {400, 402, 404}:
                        logger.warning("Model unavailable model=%s code=%s", model, exc.code)
                        break  # next model
                    if exc.code in {429, 500, 502, 503, 504}:
                        continue  # retry same model
                    raise last_error
                except (urllib.error.URLError, TimeoutError, OSError) as exc:
                    last_error = RuntimeError(f"OpenRouter network error: {exc}")
                    continue

                data = json.loads(raw)
                usage = data.get("usage") or {}
                token_usage = {
                    "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                    "completion_tokens": int(usage.get("completion_tokens") or 0),
                    "total_tokens": int(usage.get("total_tokens") or 0),
                }
                choices = data.get("choices") or []
                if not choices:
                    last_error = RuntimeError("OpenRouter: empty choices")
                    continue
                content = (choices[0].get("message") or {}).get("content")
                if content is None or (isinstance(content, str) and not content.strip()):
                    last_error = RuntimeError("OpenRouter: no message content")
                    continue
                model_used = str(data.get("model") or model)
                return str(content).strip(), model_used, token_usage, total_retries

        if last_error:
            raise last_error
        raise RuntimeError("OpenRouter: no models available")

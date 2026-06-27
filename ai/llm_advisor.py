"""Optional LLM advisor when rule confidence is below threshold."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger("ai.llm_advisor")


def suggest_recovery_action(
    *,
    classification: str,
    confidence: float,
    context: dict[str, Any],
    failed_step: str,
    module_name: str,
    allowed_actions: list[str],
) -> dict[str, Any] | None:
    """
    Returns dict with keys: action, confidence, reasoning.
    None if LLM unavailable or disabled.
    """
    try:
        from intelligent_platform.config import (
            OPENROUTER_APP_TITLE,
            OPENROUTER_BASE_URL,
            OPENROUTER_HTTP_REFERER,
            ai_health_marks_unavailable,
            openrouter_api_key,
            openrouter_model_primary,
        )
        from intelligent_platform.openrouter_client import call_openrouter
    except ImportError:
        logger.debug("intelligent_platform not available for LLM advisor")
        return None

    if ai_health_marks_unavailable():
        return None
    key = openrouter_api_key()
    if not key:
        return None

    prompt = {
        "role": "You are a mobile QA recovery advisor for Kodak Step Print Maestro tests.",
        "task": "Pick ONE recovery action from allowed_actions only.",
        "module": module_name,
        "failed_step": failed_step,
        "screen_classification": classification,
        "rule_confidence": confidence,
        "visible_text": context.get("all_visible_text", [])[:40],
        "allowed_actions": allowed_actions,
        "output_format": {"action": "string", "confidence": "0-1", "reasoning": "brief"},
    }
    messages = [
        {
            "role": "system",
            "content": "Respond with JSON only. Never suggest actions outside allowed_actions.",
        },
        {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
    ]
    try:
        raw = call_openrouter(
            messages,
            openrouter_model_primary(),
            api_key=key,
            base_url=OPENROUTER_BASE_URL,
            http_referer=OPENROUTER_HTTP_REFERER,
            app_title=OPENROUTER_APP_TITLE,
            max_tokens=200,
        )
        text = raw.strip()
        if "{" in text:
            start, end = text.find("{"), text.rfind("}")
            text = text[start : end + 1]
        data = json.loads(text)
        if isinstance(data, dict) and data.get("action") in allowed_actions:
            return data
    except Exception as ex:
        logger.warning("LLM advisor failed: %s", ex)
    return None

"""OpenAI-compatible LLM client (OpenRouter)."""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


class LLMClient:
    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key_env: str = "OPENROUTER_API_KEY",
        timeout: int = 45,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ.get(api_key_env, "").strip()
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, system: str, user: str) -> dict[str, Any]:
        if not self.available:
            return {"content": "", "error": "LLM API key not configured"}
        url = f"{self.base_url}/chat/completions"
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            return {"content": content, "raw": data}
        except Exception as ex:
            return {"content": "", "error": str(ex)}

"""Load AI engine configuration from YAML/JSON under ai/config/."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_AI_ROOT = Path(__file__).resolve().parent
_DEFAULT_CONFIG = _AI_ROOT / "config" / "ai_engine.yaml"


def _truthy(val: str | None, default: bool = False) -> bool:
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _load_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore

            data = yaml.safe_load(text)
            return data if isinstance(data, dict) else {}
        except ImportError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


@dataclass
class EngineConfig:
    enabled: bool = False
    max_recovery_attempts: int = 2
    wait_after_action_ms: int = 1500
    wait_before_retry_scan_ms: int = 3000
    screenshot_dir: str = "ai/logs/screenshots"
    decision_log_dir: str = "ai/logs/decisions"
    allow_bluetooth_enable: bool = False
    allow_app_restart: bool = False
    use_llm_when_rules_below_confidence: float = 0.55
    llm_enabled: bool = True
    printer_rules_path: str = "ai/config/printer_rules.yaml"
    popup_rules_path: str = "ai/config/popup_rules.yaml"
    permission_policy: str = "allow_while_using"
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any], repo_root: Path) -> "EngineConfig":
        engine = data.get("engine") or data
        paths = engine.get("paths") or {}
        recovery = engine.get("recovery") or {}
        llm = engine.get("llm") or {}
        permissions = engine.get("permissions") or {}

        def resolve_rel(p: str) -> str:
            if not p:
                return p
            pp = Path(p)
            if pp.is_absolute():
                return str(pp)
            return str((repo_root / p).resolve())

        return cls(
            enabled=_truthy(str(engine.get("enabled", False)), False),
            max_recovery_attempts=int(recovery.get("max_attempts", 2)),
            wait_after_action_ms=int(recovery.get("wait_after_action_ms", 1500)),
            wait_before_retry_scan_ms=int(recovery.get("wait_before_retry_scan_ms", 3000)),
            screenshot_dir=resolve_rel(str(paths.get("screenshot_dir", "ai/logs/screenshots"))),
            decision_log_dir=resolve_rel(str(paths.get("decision_log_dir", "ai/logs/decisions"))),
            allow_bluetooth_enable=_truthy(str(recovery.get("allow_bluetooth_enable", False)), False),
            allow_app_restart=_truthy(str(recovery.get("allow_app_restart", False)), False),
            use_llm_when_rules_below_confidence=float(
                llm.get("use_when_rules_below_confidence", 0.55)
            ),
            llm_enabled=_truthy(str(llm.get("enabled", True)), True),
            printer_rules_path=resolve_rel(
                str(paths.get("printer_rules", "ai/config/printer_rules.yaml"))
            ),
            popup_rules_path=resolve_rel(
                str(paths.get("popup_rules", "ai/config/popup_rules.yaml"))
            ),
            permission_policy=str(permissions.get("default", "allow_while_using")),
            raw=data,
        )


def load_engine_config(
    repo_root: Path | None = None,
    config_path: Path | None = None,
) -> EngineConfig:
    """Merge env overrides: ATP_AI_RECOVERY, ATP_AI_CONFIG."""
    root = (repo_root or Path(os.environ.get("WORKSPACE", os.getcwd()))).resolve()
    cfg_path = config_path or Path(
        os.environ.get("ATP_AI_CONFIG", str(_DEFAULT_CONFIG))
    )
    if not cfg_path.is_absolute():
        cfg_path = root / cfg_path
    data = _load_file(cfg_path)
    cfg = EngineConfig.from_dict(data, root)
    if os.environ.get("ATP_AI_RECOVERY"):
        cfg.enabled = _truthy(os.environ.get("ATP_AI_RECOVERY"), cfg.enabled)
    if os.environ.get("ATP_AI_MAX_ATTEMPTS"):
        cfg.max_recovery_attempts = int(os.environ["ATP_AI_MAX_ATTEMPTS"])
    return cfg

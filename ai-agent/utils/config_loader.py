"""Load ai-agent YAML configuration."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_DEFAULT = Path(__file__).resolve().parents[1] / "config" / "agent.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except ImportError:
        return json.loads(text) if text.strip().startswith("{") else {}


def _resolve(root: Path, rel: str) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else (root / p).resolve()


@dataclass
class AgentConfig:
    repo_root: Path
    enabled: bool
    app_package: str
    app_id: str
    mode: str
    max_recovery_attempts: int
    max_steps: int
    maestro_cmd: str
    knowledge_dir: Path
    sqlite_path: Path
    chroma_path: Path
    excel_path: Path
    dashboard_path: Path
    decision_log: Path
    summary_json: Path
    screenshot_dir: Path
    ui_dump_dir: Path
    llm_model: str
    llm_base_url: str
    llm_api_key_env: str
    min_confidence_for_llm: float
    auto_scan: bool
    rescan_if_changed: bool
    scan_paths: list[str]
    app_profile: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


def load_config(repo_root: Path, config_path: Path | None = None) -> AgentConfig:
    root = repo_root.resolve()
    cfg_path = config_path or Path(os.environ.get("AI_AGENT_CONFIG", str(_DEFAULT)))
    if not cfg_path.is_absolute():
        cfg_path = root / cfg_path
    data = _load_yaml(cfg_path)
    agent = data.get("agent") or {}
    exec_ = data.get("execution") or {}
    learn = data.get("learning") or {}
    mem = data.get("memory") or {}
    llm = data.get("llm") or {}
    rep = data.get("reporting") or {}
    vis = data.get("vision") or {}
    integ = data.get("integrations") or {}

    app_yaml = root / "ai-agent" / "config" / "app_kodak_step_print.yaml"
    app_profile = _load_yaml(app_yaml)

    mode = os.environ.get("AI_AGENT_MODE", str(exec_.get("mode", "assist"))).strip().lower()
    enabled = agent.get("enabled", True)
    if os.environ.get("AI_AGENT_ENABLED"):
        enabled = os.environ.get("AI_AGENT_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}

    return AgentConfig(
        repo_root=root,
        enabled=bool(enabled),
        app_package=str(agent.get("app_package", "com.kodak.steptouch")),
        app_id=str(agent.get("app_id", "kodak_step_print")),
        mode=mode,
        max_recovery_attempts=int(exec_.get("max_recovery_attempts", 3)),
        max_steps=int(exec_.get("max_steps_per_session", 200)),
        maestro_cmd=os.environ.get("MAESTRO_CMD", str(integ.get("maestro_cmd", "maestro.bat"))),
        knowledge_dir=_resolve(root, str(learn.get("knowledge_dir", "ai-agent/knowledge"))),
        sqlite_path=_resolve(root, str(mem.get("sqlite_path", "ai-agent/knowledge/agent_memory.db"))),
        chroma_path=_resolve(root, str(mem.get("chroma_path", "ai-agent/knowledge/chroma"))),
        excel_path=_resolve(root, str(rep.get("excel_path", "ai-agent/reports/AI_Agent_Report.xlsx"))),
        dashboard_path=_resolve(root, str(rep.get("dashboard_html", "ai-agent/reports/AI_Agent_Dashboard.html"))),
        decision_log=_resolve(root, str(rep.get("decision_log_jsonl", "ai-agent/logs/decisions/decisions.jsonl"))),
        summary_json=_resolve(root, str(rep.get("summary_json", "ai-agent/reports/execution_summary.json"))),
        screenshot_dir=_resolve(root, str(vis.get("screenshot_dir", "ai-agent/logs/screenshots"))),
        ui_dump_dir=_resolve(root, str(vis.get("ui_dump_dir", "ai-agent/logs/ui_dumps"))),
        llm_model=str(llm.get("model", "openai/gpt-4o-mini")),
        llm_base_url=str(llm.get("base_url", "https://openrouter.ai/api/v1")),
        llm_api_key_env=str(llm.get("api_key_env", "OPENROUTER_API_KEY")),
        min_confidence_for_llm=float(llm.get("min_confidence_for_llm", 0.55)),
        auto_scan=bool(learn.get("auto_scan_on_first_run", True)),
        rescan_if_changed=bool(learn.get("rescan_if_repo_changed", True)),
        scan_paths=[str(p) for p in (learn.get("scan_paths") or [])],
        app_profile=app_profile,
        raw=data,
    )

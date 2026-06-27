"""Load suite_modules.yaml with optional JSON fallback."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_DEFAULT = Path(__file__).resolve().parent / "config" / "suite_modules.yaml"


def _load_raw(path: Path) -> dict[str, Any]:
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
class ModuleSpec:
    name: str
    folder: str
    enabled: bool = True
    skip_if_folder_missing: bool = False


@dataclass
class SuiteConfig:
    name: str
    continue_on_failure: bool
    clear_state_per_module: bool
    skip_yaml_preflight_after_first: bool
    refresh_devices_each_module: bool
    optional_retry_failed: int
    build_result_on_partial_fail: str
    setup_enabled: bool
    setup_flow: str
    verify_app_installed: bool
    run_precheck: bool
    modules: list[ModuleSpec]
    summary_json: Path
    summary_txt: Path
    copy_failed_artifacts: bool
    ai_recovery_enabled: bool
    ai_max_recovery_attempts: int
    raw: dict[str, Any] = field(default_factory=dict)


def load_suite_config(repo_root: Path, config_path: Path | None = None) -> SuiteConfig:
    root = repo_root.resolve()
    cfg_path = config_path or Path(os.environ.get("ATP_SUITE_CONFIG", str(_DEFAULT)))
    if not cfg_path.is_absolute():
        cfg_path = root / cfg_path
    data = _load_raw(cfg_path)
    suite = data.get("suite") or {}
    setup = data.get("setup") or {}
    reporting = data.get("reporting") or {}
    ai = data.get("ai") or {}

    modules: list[ModuleSpec] = []
    for m in data.get("modules") or []:
        if not isinstance(m, dict):
            continue
        modules.append(
            ModuleSpec(
                name=str(m.get("name", "")).strip(),
                folder=str(m.get("folder", "")).strip(),
                enabled=bool(m.get("enabled", True)),
                skip_if_folder_missing=bool(m.get("skip_if_folder_missing", False)),
            )
        )

    def rp(key: str, default: str) -> Path:
        p = Path(str(reporting.get(key, default)))
        return p if p.is_absolute() else root / p

    setup_flow = str(setup.get("flow", "suite/flows/MasterSetup.yaml"))
    if not Path(setup_flow).is_absolute():
        setup_flow = str((root / setup_flow).resolve())

    cfg = SuiteConfig(
        name=str(suite.get("name", "ATP Complete Suite")),
        continue_on_failure=bool(suite.get("continue_on_failure", True)),
        clear_state_per_module=bool(suite.get("clear_state_per_module", False)),
        skip_yaml_preflight_after_first=bool(
            suite.get("skip_yaml_preflight_after_first_module", True)
        ),
        refresh_devices_each_module=bool(
            suite.get("refresh_devices_before_each_module", False)
        ),
        optional_retry_failed=int(suite.get("optional_retry_failed_modules", 0)),
        build_result_on_partial_fail=str(suite.get("build_result_on_partial_fail", "UNSTABLE")),
        setup_enabled=bool(setup.get("enabled", True)),
        setup_flow=setup_flow,
        verify_app_installed=bool(setup.get("verify_app_installed", True)),
        run_precheck=bool(setup.get("run_precheck", False)),
        modules=modules,
        summary_json=rp("summary_json", "build-summary/suite_execution_summary.json"),
        summary_txt=rp("summary_txt", "build-summary/suite_execution_summary.txt"),
        copy_failed_artifacts=bool(reporting.get("copy_failed_artifacts", True)),
        ai_recovery_enabled=bool(ai.get("enabled", False)),
        ai_max_recovery_attempts=int(ai.get("max_recovery_attempts_per_module", 2)),
        raw=data,
    )
    if os.environ.get("ATP_AI_RECOVERY"):
        cfg.ai_recovery_enabled = os.environ.get("ATP_AI_RECOVERY", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
    return cfg

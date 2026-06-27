"""Hybrid execution orchestrator — fast Maestro modules + smart recovery on failure."""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import yaml

from executor.decision_cache import DecisionCache
from executor.device_info import collect_device_info
from executor.knowledge_manager import KnowledgeManager
from executor.models import ModuleSummary, RunOutcome
from executor.module_executor import run_module_fast
from executor.smart_recovery import SmartRecovery
from executor.status_parser import REPORT_COLUMNS, rows_for_module
from reporting.excel_report import write_excel_report
from reporting.summary_report import write_execution_summary
from utils.config_loader import AgentConfig


@dataclass
class ModuleSpec:
    name: str
    folder: str
    enabled: bool = True
    skip_if_folder_missing: bool = False


def _load_modules(cfg: AgentConfig) -> list[ModuleSpec]:
    path = cfg.repo_root / "ai-agent" / "config" / "modules.yaml"
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: list[ModuleSpec] = []
    for m in data.get("modules") or []:
        if not isinstance(m, dict):
            continue
        out.append(
            ModuleSpec(
                name=str(m.get("name", "")),
                folder=str(m.get("folder", "")),
                enabled=bool(m.get("enabled", True)),
                skip_if_folder_missing=bool(m.get("skip_if_folder_missing", False)),
            )
        )
    exec_cfg = data.get("execution") or {}
    cfg.raw.setdefault("modules_exec", exec_cfg)
    return out


def _compute_health(summaries: list[ModuleSummary]) -> float:
    if not summaries:
        return 100.0
    scored = [1.0 if s.status.startswith("PASS") else 0.0 for s in summaries]
    return 100.0 * sum(scored) / len(scored)


def run_hybrid_agent(cfg: AgentConfig, device_id: str, mode: str) -> RunOutcome:
    t_run = time.time()
    outcome = RunOutcome()
    all_rows: list[dict[str, Any]] = []
    summaries: list[ModuleSummary] = []
    cache = DecisionCache()
    recovery_engine = SmartRecovery(cfg, device_id, cache)

    modules = _load_modules(cfg)
    exec_cfg = cfg.raw.get("modules_exec") or {}
    continue_on_fail = bool(exec_cfg.get("continue_on_failure", True))
    clear_first = bool(exec_cfg.get("clear_state_first_module", True))
    retry_after_recovery = bool(exec_cfg.get("retry_module_after_recovery", True))

    knowledge_updated = False
    knowledge_load_sec = 0.0
    device_info = collect_device_info(device_id, cfg.app_package)

    try:
        km = KnowledgeManager(cfg)
        knowledge_updated, knowledge_load_sec = km.ensure_loaded()
        print(
            f"[ai-agent] knowledge loaded updated={knowledge_updated} "
            f"duration={knowledge_load_sec:.1f}s cache_hits={cache.hits}",
            flush=True,
        )

        if mode == "observe":
            print("[ai-agent] observe mode — skipping Maestro module execution", flush=True)
        else:
            first = True
            for mod in modules:
                if not mod.enabled:
                    continue
                mod_t0 = time.time()
                clear = clear_first and first
                first = False

                result = run_module_fast(
                    cfg.repo_root,
                    folder=mod.folder,
                    module_name=mod.name,
                    app_package=cfg.app_package,
                    maestro_cmd=cfg.maestro_cmd,
                    device_id=device_id,
                    clear_state=clear,
                )

                recovery_dict: dict[str, Any] = {
                    "ai_decision": "No AI Intervention",
                    "attempts": 0,
                    "result": "N/A",
                    "retry_count": 0,
                }
                recovered = False

                if not result.passed:
                    smart = recovery_engine.try_recover(result, mode)
                    recovery_dict = smart.as_report_dict()
                    if smart.success and retry_after_recovery:
                        recovered = True
                        outcome.recovered_count += 1
                        result = run_module_fast(
                            cfg.repo_root,
                            folder=mod.folder,
                            module_name=mod.name,
                            app_package=cfg.app_package,
                            maestro_cmd=cfg.maestro_cmd,
                            device_id=device_id,
                            clear_state=False,
                        )
                        recovery_dict["result"] = "PASS" if result.passed else "FAIL"
                    elif smart.attempted and not smart.success:
                        outcome.unrecoverable_count += 1

                health = _compute_health(summaries + [ModuleSummary(mod.name, "PASS", 0)])
                mod_rows = rows_for_module(
                    cfg.repo_root,
                    module_name=mod.name,
                    suite_id=result.suite_id,
                    device_info=device_info,
                    recovery=recovery_dict,
                    overall_health=health,
                    device_id=device_id,
                )
                all_rows.extend(mod_rows)

                if result.passed:
                    status = "PASS (Recovered)" if recovered else "PASS"
                elif "skipped" in result.message.lower():
                    status = "SKIP"
                else:
                    status = "FAIL"

                summaries.append(
                    ModuleSummary(
                        name=mod.name,
                        status=status,
                        duration_sec=time.time() - mod_t0,
                        recovered=recovered,
                    )
                )
                print(
                    f"[ai-agent] module={mod.name} status={status} duration={summaries[-1].duration_sec:.1f}s",
                    flush=True,
                )

                if not result.passed and status == "FAIL" and not continue_on_fail:
                    outcome.exit_code = 2
                    break
                if not result.passed and status == "FAIL":
                    outcome.exit_code = 2

        final_health = _compute_health(summaries)
        for row in all_rows:
            row["Overall Health Score"] = f"{final_health:.0f}%"

    except Exception as ex:
        print(f"[ai-agent] ERROR during execution: {ex}", flush=True)
        outcome.exit_code = 2
        all_rows.append({col: "" for col in REPORT_COLUMNS} | {
            "Module": "SYSTEM",
            "Test Case": "execution_error",
            "Status": "FAIL",
            "Root Cause": str(ex),
            "AI Decision": "No AI Intervention",
            "Device Name": device_info.device_name,
        })

    outcome.rows = all_rows
    outcome.module_summaries = summaries
    outcome.knowledge_updated = knowledge_updated
    outcome.knowledge_load_sec = knowledge_load_sec
    outcome.total_sec = time.time() - t_run

    # Always generate reports (even on failure)
    _finalize_reports(cfg, outcome, device_id, mode, cache)
    return outcome


def _finalize_reports(
    cfg: AgentConfig,
    outcome: RunOutcome,
    device_id: str,
    mode: str,
    cache: DecisionCache,
) -> None:
    health = _compute_health(outcome.module_summaries)

    def _write_excel() -> None:
        write_excel_report(cfg.excel_path, outcome.rows or [_empty_row(cfg, device_id)])

    def _write_summary() -> None:
        write_execution_summary(
            cfg.summary_json,
            cfg.repo_root / "ai-agent" / "reports" / "execution_summary.txt",
            cfg.excel_path,
            outcome,
            health,
            mode,
            cache,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_write_excel)
        f2 = pool.submit(_write_summary)
        f1.result()
        f2.result()

    # Dashboard JSON for optional HTML refresh
    dash = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "health_percent": health,
        "modules": [{"name": s.name, "status": s.status} for s in outcome.module_summaries],
        "excel": str(cfg.excel_path),
    }
    cfg.summary_json.parent.mkdir(parents=True, exist_ok=True)
    cfg.summary_json.write_text(json.dumps(dash, indent=2), encoding="utf-8")


def _empty_row(cfg: AgentConfig, device_id: str) -> dict[str, Any]:
    return {col: "" for col in REPORT_COLUMNS} | {
        "Module": "N/A",
        "Test Case": "No test data",
        "Status": "UNKNOWN",
        "AI Decision": "No AI Intervention",
        "Device Name": device_id,
        "Overall Health Score": "0%",
    }

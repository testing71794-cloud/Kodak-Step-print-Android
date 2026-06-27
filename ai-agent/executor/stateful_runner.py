"""Stateful session orchestrator — one app journey, adaptive waits, checkpoints."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from executor.decision_cache import DecisionCache
from executor.device_info import collect_device_info
from executor.hybrid_runner import ModuleSpec, _load_modules, _compute_health
from executor.knowledge_manager import KnowledgeManager
from executor.models import ModuleSummary, RunOutcome
from executor.module_executor import run_module_fast
from executor.smart_recovery import SmartRecovery
from executor.status_parser import REPORT_COLUMNS, rows_for_module
from integrations.adb_client import ADBClient
from learning.artifact_learner import ArtifactLearner
from memory.sqlite_store import SQLiteMemoryStore
from memory.timing_store import TimingStore
from reporting.excel_report import write_excel_report
from reporting.summary_report import write_execution_summary
from session.adaptive_wait import AdaptiveWait
from session.navigation import NavigationEngine
from session.relaunch_policy import evaluate_relaunch
from session.screen_monitor import ScreenMonitor
from session.session_manager import ExecutionSession
from utils.config_loader import AgentConfig
from vision.screen_capture import VisionEngine


def run_stateful_agent(cfg: AgentConfig, device_id: str, mode: str) -> RunOutcome:
    t_run = time.time()
    outcome = RunOutcome()
    all_rows: list[dict[str, Any]] = []
    summaries: list[ModuleSummary] = []
    cache = DecisionCache()

    memory = SQLiteMemoryStore(cfg.sqlite_path)
    timing = TimingStore(cfg.sqlite_path.parent / "timing_stats.db")
    adb = ADBClient(device_id, cfg.app_package)
    vision = VisionEngine(adb, cfg.screenshot_dir, cfg.ui_dump_dir)
    waiter = AdaptiveWait(timing, default_timeout=12.0, poll_interval=0.35)
    monitor = ScreenMonitor(adb, vision)
    nav = NavigationEngine(adb, vision, waiter)
    recovery_engine = SmartRecovery(cfg, device_id, cache)

    session = ExecutionSession.create(device_id, mode)
    device_info = collect_device_info(device_id, cfg.app_package)
    exec_cfg = cfg.raw.get("modules_exec") or {}
    continue_on_fail = bool(exec_cfg.get("continue_on_failure", True))
    retry_after_recovery = bool(exec_cfg.get("retry_module_after_recovery", True))

    knowledge_updated = False
    knowledge_load_sec = 0.0
    artifacts_learned = 0

    try:
        km = KnowledgeManager(cfg)
        knowledge_updated, knowledge_load_sec = km.ensure_loaded()
        session.metrics.knowledge_updated = knowledge_updated

        learner = ArtifactLearner(cfg.repo_root, memory)
        artifacts_learned, artifacts_changed = learner.ingest()
        session.metrics.artifacts_learned = artifacts_learned
        if artifacts_changed:
            session.metrics.knowledge_updated = True

        print(
            f"[ai-agent.session] id={session.session_id} knowledge={knowledge_load_sec:.1f}s "
            f"artifacts_new={artifacts_learned}",
            flush=True,
        )

        if mode == "observe":
            print("[ai-agent.session] observe — no Maestro execution", flush=True)
        else:
            modules = [m for m in nav.order_modules(_load_modules(cfg)) if m.enabled]
            previous_duration = _load_previous_duration(memory)

            for mod in modules:
                session.current_module = mod.name
                mod_t0 = time.time()

                # Navigate from current state — avoid home reset
                nav_result = nav.navigate_to_module(mod.name)
                if nav_result.action.startswith("tap:"):
                    session.metrics.navigation_optimisations += 1
                    monitor.wait_until_idle(waiter, f"after_{mod.name}")

                clear = session.should_clear_state()
                if clear:
                    session.mark_launch()
                else:
                    print(f"[ai-agent.session] warm continue → {mod.name}", flush=True)

                result = run_module_fast(
                    cfg.repo_root,
                    folder=mod.folder,
                    module_name=mod.name,
                    app_package=cfg.app_package,
                    maestro_cmd=cfg.maestro_cmd,
                    device_id=device_id,
                    clear_state=clear,
                    warm_session=not clear,
                )

                # Adaptive idle wait — proceed as soon as UI settles (no static 10–20s)
                monitor.wait_until_idle(waiter, f"post_{mod.name}", timeout=8.0)
                session.metrics.adaptive_wait_saved_sec += waiter.total_saved_sec

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
                    relaunch = evaluate_relaunch(
                        failure_message=result.message,
                        recovery_exhausted=smart.attempted and not smart.success,
                    )
                    if relaunch.should_relaunch:
                        session.mark_restart(relaunch.reason)
                        recovery_dict["ai_decision"] = f"relaunch:{relaunch.reason}"
                        result = run_module_fast(
                            cfg.repo_root,
                            folder=mod.folder,
                            module_name=mod.name,
                            app_package=cfg.app_package,
                            maestro_cmd=cfg.maestro_cmd,
                            device_id=device_id,
                            clear_state=True,
                            warm_session=False,
                        )
                    elif smart.success and retry_after_recovery:
                        recovered = True
                        outcome.recovered_count += 1
                        session.metrics.checkpoint_resumes += 1
                        result = run_module_fast(
                            cfg.repo_root,
                            folder=mod.folder,
                            module_name=mod.name,
                            app_package=cfg.app_package,
                            maestro_cmd=cfg.maestro_cmd,
                            device_id=device_id,
                            clear_state=False,
                            warm_session=True,
                        )
                        recovery_dict["result"] = "PASS" if result.passed else "FAIL"
                    elif smart.attempted and not smart.success:
                        outcome.unrecoverable_count += 1

                if result.passed:
                    session.mark_module_checkpoint(mod.name, True)

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
                for row in mod_rows:
                    row["Session ID"] = session.session_id
                    row["Launch Count"] = session.metrics.launch_count
                    row["Restart Count"] = session.metrics.restart_count
                all_rows.extend(mod_rows)

                if result.passed:
                    status = "PASS (Recovered)" if recovered else "PASS"
                elif "skipped" in result.message.lower():
                    status = "SKIP"
                else:
                    status = "FAIL"

                mod_duration = time.time() - mod_t0
                summaries.append(
                    ModuleSummary(
                        name=mod.name,
                        status=status,
                        duration_sec=mod_duration,
                        recovered=recovered,
                    )
                )
                timing.record(f"module_{mod.name}", mod_duration)
                print(
                    f"[ai-agent.session] {mod.name} {status} {mod_duration:.1f}s "
                    f"launches={session.metrics.launch_count}",
                    flush=True,
                )

                if status == "FAIL":
                    outcome.exit_code = 2
                    if not continue_on_fail:
                        break

            session.metrics.avg_screen_load_sec = _avg_timing(timing)
            if previous_duration and outcome.total_sec == 0:
                pass
            total = time.time() - t_run
            if previous_duration > 0:
                session.metrics.performance_vs_previous_pct = (
                    (previous_duration - total) / previous_duration * 100.0
                )

        final_health = _compute_health(summaries)
        for row in all_rows:
            row["Overall Health Score"] = f"{final_health:.0f}%"

    except Exception as ex:
        print(f"[ai-agent.session] ERROR: {ex}", flush=True)
        outcome.exit_code = 2
        all_rows.append(
            {col: "" for col in REPORT_COLUMNS}
            | {
                "Module": "SYSTEM",
                "Test Case": "session_error",
                "Status": "FAIL",
                "Root Cause": str(ex),
                "AI Decision": "No AI Intervention",
                "Device Name": device_info.device_name,
            }
        )

    outcome.rows = all_rows
    outcome.module_summaries = summaries
    outcome.knowledge_updated = session.metrics.knowledge_updated
    outcome.knowledge_load_sec = knowledge_load_sec
    outcome.total_sec = time.time() - t_run
    outcome.session_metrics = session.metrics

    _finalize_reports(cfg, outcome, device_id, mode, cache, session)
    _persist_session(memory, session, outcome)
    return outcome


def _avg_timing(timing: TimingStore) -> float:
    stats = timing.summary()
    if not stats:
        return 0.0
    return sum(float(s.get("last_sec") or 0) for s in stats) / len(stats)


def _load_previous_duration(memory: SQLiteMemoryStore) -> float:
    prev = memory.get("session_history", "last_run")
    if prev:
        return float(prev.get("total_sec", 0) or 0)
    return 0.0


def _persist_session(memory: SQLiteMemoryStore, session: ExecutionSession, outcome: RunOutcome) -> None:
    from memory.sqlite_store import MemoryRecord

    memory.upsert(
        MemoryRecord(
            "session_history",
            "last_run",
            {
                "session_id": session.session_id,
                "total_sec": outcome.total_sec,
                "launch_count": session.metrics.launch_count,
                "restart_count": session.metrics.restart_count,
                "health": _compute_health(outcome.module_summaries),
            },
        )
    )


def _finalize_reports(
    cfg: AgentConfig,
    outcome: RunOutcome,
    device_id: str,
    mode: str,
    cache: DecisionCache,
    session: ExecutionSession,
) -> None:
    health = _compute_health(outcome.module_summaries)
    metrics = session.metrics

    def _write_excel() -> None:
        write_excel_report(
            cfg.excel_path,
            outcome.rows or [_empty_row(cfg, device_id)],
            session_metrics=metrics,
            module_summaries=outcome.module_summaries,
        )

    def _write_summary() -> None:
        write_execution_summary(
            cfg.summary_json,
            cfg.repo_root / "ai-agent" / "reports" / "execution_summary.txt",
            cfg.excel_path,
            outcome,
            health,
            mode,
            cache,
            session_metrics=metrics,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        pool.submit(_write_excel).result()
        pool.submit(_write_summary).result()

    dash = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session.session_id,
        "health_percent": health,
        "launch_count": metrics.launch_count,
        "restart_count": metrics.restart_count,
        "adaptive_wait_saved_sec": metrics.adaptive_wait_saved_sec,
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

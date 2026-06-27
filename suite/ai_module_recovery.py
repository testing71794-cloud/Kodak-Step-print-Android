"""AI Decision Engine hook — module-level recovery after Maestro failure (optional)."""

from __future__ import annotations

import os
from pathlib import Path

from suite.module_runner import ModuleResult, run_module
from suite.setup_runner import read_detected_devices


def try_ai_recovery_and_retry_module(
    repo: Path,
    spec,
    *,
    app_package: str,
    maestro_cmd: str,
    failed_result: ModuleResult,
    max_attempts: int = 2,
) -> ModuleResult:
    """
    On module failure: capture screen, classify state, execute recovery action,
    then re-run the module once (clear_state=false).

    Does not modify existing Maestro YAML or jenkins_atp_stage.py.
    """
    devices = read_detected_devices(repo)
    device_id = devices[0] if devices else os.environ.get("ATP_SUITE_DEVICE", "")
    if not device_id:
        print("[suite.ai] no device for AI recovery — skipping", flush=True)
        return failed_result

    try:
        from ai.ai_decision_engine import AIDecisionEngine
        from ai.config_loader import load_engine_config
        from ai.recovery_manager import RecoveryManager
    except ImportError as ex:
        print(f"[suite.ai] AI package unavailable: {ex}", flush=True)
        return failed_result

    cfg = load_engine_config(repo)
    cfg.enabled = True
    if os.environ.get("ATP_AI_RECOVERY", "").strip().lower() in ("0", "false", "no", "off"):
        return failed_result

    engine = AIDecisionEngine(cfg, repo, device_id, app_package)
    manager = RecoveryManager(
        cfg,
        device_id,
        spec.name,
        str(repo / "ATP TestCase Flows" / spec.folder),
        app_package,
    )

    maestro_error = failed_result.message
    for attempt in range(1, max_attempts + 1):
        print(
            f"[suite.ai] recovery attempt {attempt}/{max_attempts} module={spec.name!r}",
            flush=True,
        )
        plan = engine.analyze_failure(
            module_name=spec.name,
            failed_step=maestro_error,
            maestro_error=maestro_error,
        )
        outcome = manager.attempt_recovery(
            plan,
            failed_step=maestro_error,
            attempt=attempt,
        )
        if not outcome.recovered:
            continue

        retry = run_module(
            repo,
            spec,
            app_package=app_package,
            maestro_cmd=maestro_cmd,
            clear_state=False,
            skip_yaml_preflight=True,
            refresh_devices=False,
            retry_attempt=attempt,
        )
        retry.message = f"{retry.message}; ai_recovery={outcome.last_action}"
        if retry.status == "PASS":
            return retry
        maestro_error = retry.message

    failed_result.message = f"{failed_result.message}; ai_recovery=exhausted"
    return failed_result

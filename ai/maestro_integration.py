"""
Maestro integration — opt-in wrapper that invokes AI recovery ONLY on Maestro failure.

Does NOT modify existing flows, Jenkinsfile, or orchestrator code.
Use instead of direct `maestro test` when AI recovery is desired:

  set ATP_AI_RECOVERY=1
  python -m ai.maestro_integration --device SERIAL --flow "path/to/flow.yaml" --module connection

Or:
  python scripts/maestro_ai_recovery_wrapper.py --device SERIAL --flow ...
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from ai.ai_decision_engine import AIDecisionEngine, RecoveryOutcome  # noqa: E402
from ai.config_loader import load_engine_config  # noqa: E402
from ai.recovery_manager import RecoveryManager  # noqa: E402


def _find_latest_maestro_log() -> Path | None:
    tests_root = Path.home() / ".maestro" / "tests"
    if not tests_root.is_dir():
        return None
    logs = sorted(tests_root.glob("*/maestro.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def _read_failure_from_log(log_path: Path | None) -> str:
    if not log_path or not log_path.is_file():
        return ""
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return AIDecisionEngine.parse_maestro_failure(text)


def _resolve_maestro_cmd(explicit: str | None) -> list[str]:
    cmd = explicit or os.environ.get("MAESTRO_CMD", "maestro.bat")
    if os.name == "nt" and not cmd.lower().endswith(".bat"):
        bat = Path(cmd).with_suffix(".bat")
        if bat.is_file():
            cmd = str(bat)
    return [cmd]


def run_maestro(
    *,
    device_id: str,
    flow_path: Path,
    maestro_cmd: str | None = None,
    debug_output: Path | None = None,
) -> tuple[int, Path | None]:
    flow_path = flow_path.resolve()
    if not flow_path.is_file():
        raise FileNotFoundError(flow_path)

    launcher = _resolve_maestro_cmd(maestro_cmd)
    argv = [*launcher, "--device", device_id, "test", str(flow_path)]
    if debug_output:
        argv.extend(["--debug-output", str(debug_output)])

    print(f"[ai.maestro_integration] maestro: {' '.join(argv)}", flush=True)
    p = subprocess.run(argv, cwd=str(_REPO))
    log = _find_latest_maestro_log()
    return p.returncode, log


def run_with_ai_recovery(
    *,
    device_id: str,
    flow_path: Path,
    module_name: str,
    app_package: str = "com.kodak.steptouch",
    maestro_cmd: str | None = None,
    config_path: Path | None = None,
) -> RecoveryOutcome:
    """
    1. Run Maestro flow.
    2. On failure only: AI analyze → recover → re-run Maestro (bounded attempts).
    3. Return outcome; exit code for CLI derived from recovered flag.
    """
    cfg = load_engine_config(_REPO, config_path)
    if os.environ.get("ATP_AI_RECOVERY"):
        cfg.enabled = os.environ.get("ATP_AI_RECOVERY", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    flow_str = str(flow_path.resolve())
    rc, log_path = run_maestro(device_id=device_id, flow_path=flow_path, maestro_cmd=maestro_cmd)
    if rc == 0:
        return RecoveryOutcome(
            recovered=True,
            attempts=0,
            classification="n/a",
            last_reasoning="Maestro passed without AI",
            skipped=True,
            skip_reason="not_needed",
        )

    if not cfg.enabled:
        err = _read_failure_from_log(log_path)
        return RecoveryOutcome(
            recovered=False,
            attempts=0,
            classification="unknown",
            last_reasoning=f"AI disabled; maestro failed: {err}",
            skipped=True,
            skip_reason="ai_disabled",
        )

    engine = AIDecisionEngine(cfg, _REPO, device_id, app_package)
    manager = RecoveryManager(cfg, device_id, module_name, flow_str, app_package)
    maestro_error = _read_failure_from_log(log_path)
    failed_step = maestro_error or "unknown_step"
    last_plan = None

    for attempt in range(1, cfg.max_recovery_attempts + 1):
        print(
            f"[ai.maestro_integration] recovery attempt {attempt}/{cfg.max_recovery_attempts}",
            flush=True,
        )
        plan = engine.analyze_failure(
            module_name=module_name,
            failed_step=failed_step,
            maestro_error=maestro_error,
        )
        last_plan = plan
        result = manager.attempt_recovery(plan, failed_step=failed_step, attempt=attempt)
        if not result.recovered:
            continue

        rc2, log_path2 = run_maestro(device_id=device_id, flow_path=flow_path, maestro_cmd=maestro_cmd)
        if rc2 == 0:
            return RecoveryOutcome(
                recovered=True,
                attempts=attempt,
                classification=plan.classification,
                last_reasoning=plan.reasoning,
            )
        maestro_error = _read_failure_from_log(log_path2)
        failed_step = maestro_error or failed_step
        time.sleep(cfg.wait_after_action_ms / 1000.0)

    return RecoveryOutcome(
        recovered=False,
        attempts=cfg.max_recovery_attempts,
        classification=last_plan.classification if last_plan else "unknown",
        last_reasoning=last_plan.reasoning if last_plan else maestro_error,
    )


def _infer_module_from_flow(flow_path: Path) -> str:
    parts = flow_path.as_posix().split("/")
    if "ATP TestCase Flows" in parts:
        idx = parts.index("ATP TestCase Flows")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    m = re.search(r"([A-Z]{2})_\d", flow_path.name)
    if m:
        prefix = m.group(1).lower()
        mapping = {"co": "connection", "pr": "printing", "pm": "permission", "ed": "editing"}
        return mapping.get(prefix, prefix)
    return "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Maestro with optional AI recovery on failure")
    parser.add_argument("--device", required=True, help="Android device serial")
    parser.add_argument("--flow", required=True, help="Path to Maestro flow YAML")
    parser.add_argument("--module", default="", help="ATP module name (auto-inferred if omitted)")
    parser.add_argument("--app-package", default="com.kodak.steptouch")
    parser.add_argument("--maestro-cmd", default="", help="Maestro launcher (default: MAESTRO_CMD env)")
    parser.add_argument("--config", default="", help="Path to ai_engine.yaml")
    parser.add_argument(
        "--ai-recovery",
        action="store_true",
        help="Enable AI recovery (or set ATP_AI_RECOVERY=1)",
    )
    args = parser.parse_args(argv)

    if args.ai_recovery:
        os.environ["ATP_AI_RECOVERY"] = "1"

    flow = Path(args.flow)
    if not flow.is_absolute():
        flow = (_REPO / flow).resolve()
    module = args.module or _infer_module_from_flow(flow)
    cfg_path = Path(args.config) if args.config else None

    outcome = run_with_ai_recovery(
        device_id=args.device,
        flow_path=flow,
        module_name=module,
        app_package=args.app_package,
        maestro_cmd=args.maestro_cmd or None,
        config_path=cfg_path,
    )

    print(
        f"[ai.maestro_integration] outcome recovered={outcome.recovered} "
        f"attempts={outcome.attempts} classification={outcome.classification!r}",
        flush=True,
    )
    if outcome.skipped and outcome.skip_reason == "not_needed":
        return 0
    if outcome.skipped and outcome.skip_reason == "ai_disabled":
        return 1
    return 0 if outcome.recovered else 1


if __name__ == "__main__":
    raise SystemExit(main())

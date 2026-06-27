"""AI Step Print Agent — entry point."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_AGENT_ROOT = Path(__file__).resolve().parent
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))

from executor.stateful_runner import run_stateful_agent  # noqa: E402
from utils.config_loader import load_config  # noqa: E402
from utils.device_manager import list_devices  # noqa: E402
from utils.logging_utils import append_jsonl, setup_logging  # noqa: E402


def run_agent(
    repo_root: Path,
    *,
    mode: str | None = None,
    device_id: str | None = None,
    maestro_cmd: str | None = None,
) -> int:
    cfg = load_config(repo_root)
    if not cfg.enabled:
        print("[ai-agent] disabled — exiting without changes", flush=True)
        return 0

    if maestro_cmd:
        cfg.maestro_cmd = maestro_cmd
    if mode:
        cfg.mode = mode

    log = setup_logging(cfg.repo_root / "ai-agent" / "logs")
    log.info("AI Step Print Agent starting mode=%s (hybrid execution)", cfg.mode)

    devices = [device_id] if device_id else list_devices(repo_root)
    if not devices:
        log.error("No devices found")
        # Still write empty report
        from reporting.excel_report import write_excel_report
        from executor.status_parser import REPORT_COLUMNS

        write_excel_report(
            cfg.excel_path,
            [{**{c: "" for c in REPORT_COLUMNS}, "Status": "FAIL", "Root Cause": "No devices"}],
        )
        return 1

    overall_rc = 0
    for dev in devices:
        outcome = run_stateful_agent(cfg, dev, cfg.mode)
        for msg in [
            f"device={dev} modules={len(outcome.module_summaries)} "
            f"health_rows={len(outcome.rows)} rc={outcome.exit_code}"
        ]:
            log.info(msg)
        append_jsonl(
            cfg.decision_log,
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "device": dev,
                "mode": cfg.mode,
                "exit_code": outcome.exit_code,
                "modules": [{"name": m.name, "status": m.status} for m in outcome.module_summaries],
                "excel": str(cfg.excel_path),
            },
        )
        if outcome.exit_code != 0:
            overall_rc = 2

    print(f"[ai-agent] finished rc={overall_rc} report={cfg.excel_path}", flush=True)
    return overall_rc


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Step Print Agent (isolated module)")
    parser.add_argument("--repo", default=".", help="Repository root")
    parser.add_argument(
        "--mode",
        choices=["observe", "assist", "autonomous"],
        default=None,
        help="Execution mode",
    )
    parser.add_argument("--device", default=None, help="ADB device serial")
    parser.add_argument("--maestro-cmd", default=None, help="Maestro launcher")
    args = parser.parse_args()
    return run_agent(
        Path(args.repo).resolve(),
        mode=args.mode,
        device_id=args.device,
        maestro_cmd=args.maestro_cmd,
    )


if __name__ == "__main__":
    raise SystemExit(main())

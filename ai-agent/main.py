"""AI Step Print Agent — entry point."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure ai-agent/ is on sys.path for isolated imports
_AGENT_ROOT = Path(__file__).resolve().parent
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))

from graph.workflow import _state_to_dict, build_workflow, new_session  # noqa: E402
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
    log.info("AI Step Print Agent starting mode=%s", cfg.mode)

    devices = [device_id] if device_id else list_devices(repo_root)
    if not devices:
        log.error("No devices found")
        return 1

    overall_rc = 0
    all_rows: list[dict] = []

    for dev in devices:
        graph, _ctx = build_workflow(cfg, dev)
        state = new_session(cfg, dev, cfg.mode)
        payload = _state_to_dict(state)
        payload["device_id"] = dev
        payload["mode"] = cfg.mode
        payload["_state_obj"] = state

        result = graph.invoke(payload)
        st = result.get("_state_obj")
        if st:
            all_rows.extend(st.rows)
            for msg in st.messages:
                log.info(msg)
            append_jsonl(
                cfg.decision_log,
                {
                    "session_id": st.session_id,
                    "device": dev,
                    "mode": cfg.mode,
                    "status": st.status,
                    "decision": st.decision,
                    "recovery": st.recovery,
                },
            )
            if st.status not in ("passed", "running"):
                overall_rc = 2

    summary = {
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "mode": cfg.mode,
        "devices": devices,
        "run_count": len(all_rows),
        "status": "PASS" if overall_rc == 0 else "UNSTABLE",
    }
    cfg.summary_json.parent.mkdir(parents=True, exist_ok=True)
    cfg.summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log.info("AI Step Print Agent finished rc=%s", overall_rc)
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

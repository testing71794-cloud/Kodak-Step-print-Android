"""Parse status/*.txt into AI Agent report rows (read-only, no execution imports)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from executor.device_info import DeviceInfo

REPORT_COLUMNS = [
    "Module",
    "Test Case",
    "Status",
    "Start Time",
    "End Time",
    "Duration",
    "AI Decision",
    "Recovery Attempt",
    "Recovery Result",
    "Root Cause",
    "Suggested Fix",
    "Confidence Score",
    "Retry Count",
    "Screenshot Path",
    "Log Path",
    "Device Name",
    "Printer Name",
    "Android Version",
    "App Version",
    "Firmware Version",
    "Severity",
    "Priority",
    "Overall Health Score",
    "Session ID",
    "Launch Count",
    "Restart Count",
]


def parse_status_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.is_file():
        return data
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            data[k.strip().lower()] = v.strip()
    if not data.get("flow"):
        parts = path.stem.split("__")
        if len(parts) >= 3:
            data.setdefault("suite", parts[0])
            data.setdefault("flow", parts[1])
            data.setdefault("device", parts[2])
    return data


def _ms_to_duration(ms: str) -> str:
    try:
        n = int(ms)
    except (TypeError, ValueError):
        return ""
    if n < 1000:
        return f"{n}ms"
    return f"{n / 1000:.1f}s"


def rows_for_module(
    repo: Path,
    *,
    module_name: str,
    suite_id: str,
    device_info: DeviceInfo,
    recovery: dict[str, Any],
    overall_health: float,
    device_id: str,
) -> list[dict[str, Any]]:
    status_dir = repo / "status"
    pattern = f"{suite_id}__*__*.txt"
    files = sorted(status_dir.glob(pattern)) if status_dir.is_dir() else []
    if not files:
        return [
            _placeholder_row(
                module_name,
                "(module run — no status files)",
                "UNKNOWN",
                device_info,
                recovery,
                overall_health,
            )
        ]

    rows: list[dict[str, Any]] = []
    for sf in files:
        fields = parse_status_file(sf)
        if fields.get("device") and fields["device"] != device_id:
            continue
        status = (fields.get("status") or "UNKNOWN").upper()
        if status == "RUNNING":
            continue
        log_path = fields.get("log", "")
        if log_path and not Path(log_path).is_absolute():
            log_path = str((repo / log_path).resolve()) if (repo / log_path).exists() else log_path

        ai_decision = recovery.get("ai_decision", "No AI Intervention")
        if status == "PASS" and not recovery.get("attempted"):
            ai_decision = "No AI Intervention"

        rows.append(
            {
                "Module": module_name,
                "Test Case": fields.get("flow", sf.stem),
                "Status": status,
                "Start Time": fields.get("started_at", fields.get("timestamp", "")),
                "End Time": fields.get("finished_at", datetime.now(timezone.utc).isoformat()),
                "Duration": _ms_to_duration(fields.get("duration_ms", "")),
                "AI Decision": ai_decision,
                "Recovery Attempt": recovery.get("attempts", 0),
                "Recovery Result": recovery.get("result", "N/A"),
                "Root Cause": recovery.get("root_cause", fields.get("reason", "")),
                "Suggested Fix": recovery.get("suggested_fix", ""),
                "Confidence Score": recovery.get("confidence", ""),
                "Retry Count": recovery.get("retry_count", 0),
                "Screenshot Path": recovery.get("screenshot", ""),
                "Log Path": log_path,
                "Device Name": device_info.device_name,
                "Printer Name": device_info.printer_name,
                "Android Version": device_info.android_version,
                "App Version": device_info.app_version,
                "Firmware Version": device_info.firmware_version,
                "Severity": recovery.get("severity", ""),
                "Priority": recovery.get("priority", ""),
                "Overall Health Score": f"{overall_health:.0f}%",
            }
        )
    return rows or [
        _placeholder_row(module_name, "(no matching status)", "UNKNOWN", device_info, recovery, overall_health)
    ]


def _placeholder_row(
    module: str,
    case: str,
    status: str,
    device_info: DeviceInfo,
    recovery: dict[str, Any],
    health: float,
) -> dict[str, Any]:
    return {col: "" for col in REPORT_COLUMNS} | {
        "Module": module,
        "Test Case": case,
        "Status": status,
        "AI Decision": recovery.get("ai_decision", "No AI Intervention"),
        "Recovery Attempt": recovery.get("attempts", 0),
        "Recovery Result": recovery.get("result", "N/A"),
        "Device Name": device_info.device_name,
        "Android Version": device_info.android_version,
        "App Version": device_info.app_version,
        "Overall Health Score": f"{health:.0f}%",
    }

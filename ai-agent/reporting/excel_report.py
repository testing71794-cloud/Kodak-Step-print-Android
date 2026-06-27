"""Generate AI_Agent_Report.xlsx — always written, pass or fail."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from executor.status_parser import REPORT_COLUMNS


def write_excel_report(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = [_normalize_row(r) for r in rows] if rows else [_blank_row()]

    try:
        from openpyxl import Workbook  # type: ignore
        from openpyxl.styles import Font  # type: ignore

        wb = Workbook()
        ws = wb.active
        ws.title = "AI Agent Runs"
        ws.append(REPORT_COLUMNS)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for row in normalized:
            ws.append([row.get(c, "") for c in REPORT_COLUMNS])

        summary = wb.create_sheet("Summary")
        passed = sum(1 for r in normalized if str(r.get("Status", "")).upper() == "PASS")
        failed = sum(1 for r in normalized if str(r.get("Status", "")).upper() == "FAIL")
        recovered = sum(
            1 for r in normalized if str(r.get("Recovery Result", "")).upper() == "PASS"
        )
        summary.append(["Metric", "Value"])
        summary.append(["Total Test Rows", len(normalized)])
        summary.append(["Passed", passed])
        summary.append(["Failed", failed])
        summary.append(["Recovered", recovered])
        health_vals = [
            float(str(r.get("Overall Health Score", "0")).rstrip("%") or 0)
            for r in normalized
            if r.get("Overall Health Score")
        ]
        if health_vals:
            summary.append(["Overall Health Score", f"{health_vals[-1]:.0f}%"])
        wb.save(path)
        print(f"[ai-agent.report] wrote {path}", flush=True)
    except ImportError:
        _write_csv_fallback(path.with_suffix(".csv"), normalized)


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    out = {c: row.get(c, "") for c in REPORT_COLUMNS}
    if not out.get("AI Decision"):
        out["AI Decision"] = "No AI Intervention"
    return out


def _blank_row() -> dict[str, Any]:
    row = {c: "" for c in REPORT_COLUMNS}
    row["AI Decision"] = "No AI Intervention"
    row["Status"] = "UNKNOWN"
    return row


def _write_csv_fallback(path: Path, rows: list[dict[str, Any]]) -> None:
    import csv

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=REPORT_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

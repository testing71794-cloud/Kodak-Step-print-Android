"""Generate AI_Agent_Report.xlsx — separate from existing Excel pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def write_excel_report(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from openpyxl import Workbook  # type: ignore
        from openpyxl.styles import Font  # type: ignore

        wb = Workbook()
        ws = wb.active
        ws.title = "AI Agent Runs"
        headers = list(rows[0].keys()) if rows else [
            "Module", "Test Case", "Status", "Root Cause", "Suggested Fix", "Confidence"
        ]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for row in rows:
            ws.append([row.get(h, "") for h in headers])
        summary = wb.create_sheet("Summary")
        passed = sum(1 for r in rows if str(r.get("Status", "")).lower() == "passed")
        failed = len(rows) - passed
        summary.append(["Metric", "Value"])
        summary.append(["Total Runs", len(rows)])
        summary.append(["Passed", passed])
        summary.append(["Failed", failed])
        recovered = sum(1 for r in rows if r.get("Recovery Result") == "PASS")
        summary.append(["Recovered", recovered])
        wb.save(path)
    except ImportError:
        _write_csv_fallback(path.with_suffix(".csv"), rows)


def _write_csv_fallback(path: Path, rows: list[dict[str, Any]]) -> None:
    import csv

    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

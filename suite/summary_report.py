"""Suite execution summary — console, JSON, and text report."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from suite.config_loader import SuiteConfig
from suite.module_runner import ModuleResult
from suite.setup_runner import SetupResult


@dataclass
class SuiteExecutionReport:
    suite_name: str
    started_at: str
    finished_at: str
    total_duration_sec: float
    setup: dict
    modules: list[dict]
    total_modules: int
    passed: int
    failed: int
    skipped: int
    overall_status: str  # SUCCESS | UNSTABLE | FAILURE


def build_report(
    config: SuiteConfig,
    *,
    setup: SetupResult,
    module_results: list[ModuleResult],
    started_at: float,
    finished_at: float,
) -> SuiteExecutionReport:
    passed = sum(1 for m in module_results if m.status == "PASS")
    failed = sum(1 for m in module_results if m.status == "FAIL")
    skipped = sum(1 for m in module_results if m.status == "SKIP")
    total = len(module_results)

    if not setup.success:
        overall = "FAILURE"
    elif failed == 0:
        overall = "SUCCESS"
    else:
        overall = config.build_result_on_partial_fail.upper()
        if overall not in {"UNSTABLE", "FAILURE"}:
            overall = "UNSTABLE"

    return SuiteExecutionReport(
        suite_name=config.name,
        started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started_at)),
        finished_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(finished_at)),
        total_duration_sec=round(finished_at - started_at, 2),
        setup={
            "success": setup.success,
            "message": setup.message,
            "duration_sec": round(setup.duration_sec, 2),
            "devices": setup.devices,
        },
        modules=[asdict(m) for m in module_results],
        total_modules=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        overall_status=overall,
    )


def format_console_summary(report: SuiteExecutionReport) -> str:
    lines = [
        "",
        "=" * 59,
        "Execution Summary",
        "=" * 59,
        "",
    ]
    name_w = max((len(m["name"]) for m in report.modules), default=8)
    name_w = max(name_w, 12)
    for m in report.modules:
        status = m["status"]
        pad = " " * (name_w - len(m["name"]))
        dur = m.get("duration_sec", 0)
        lines.append(f"{m['name']}{pad}  {status:<4}  ({dur:.1f}s)")
    lines.extend(
        [
            "",
            f"Total Modules : {report.total_modules}",
            f"Passed        : {report.passed}",
            f"Failed        : {report.failed}",
            f"Skipped       : {report.skipped}",
            f"Setup         : {'OK' if report.setup.get('success') else 'FAIL'}",
            f"Total Time    : {report.total_duration_sec:.1f}s",
            f"Overall       : {report.overall_status}",
            "=" * 59,
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(report: SuiteExecutionReport, config: SuiteConfig) -> None:
    config.summary_json.parent.mkdir(parents=True, exist_ok=True)
    config.summary_txt.parent.mkdir(parents=True, exist_ok=True)
    config.summary_json.write_text(
        json.dumps(asdict(report), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    config.summary_txt.write_text(format_console_summary(report), encoding="utf-8")
    print(format_console_summary(report), flush=True)


def collect_failed_module_artifacts(repo: Path, results: list[ModuleResult]) -> None:
    """Index failed module logs for build-summary/suite-failures/."""
    dest_root = repo / "build-summary" / "suite-failures"
    dest_root.mkdir(parents=True, exist_ok=True)
    index: list[dict] = []
    for m in results:
        if m.status != "FAIL":
            continue
        sid = m.suite_id
        rep = repo / "reports" / sid
        csv_files = list((rep / "results").glob("*.csv")) if (rep / "results").is_dir() else []
        entry = {
            "module": m.name,
            "suite_id": sid,
            "logs": str(rep / "logs") if (rep / "logs").is_dir() else "",
            "results_csv": str(csv_files[0]) if csv_files else "",
        }
        index.append(entry)
    (dest_root / "failed_modules_index.json").write_text(
        json.dumps(index, indent=2),
        encoding="utf-8",
    )

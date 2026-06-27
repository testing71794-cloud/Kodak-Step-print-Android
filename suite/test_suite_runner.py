"""
Complete ATP Test Suite Runner — production orchestration layer.

- Runs shared setup ONCE (MasterSetup.yaml + device verification).
- Executes configured modules sequentially via existing jenkins_atp_stage.py.
- NEVER stops on module failure (continue_on_failure).
- Generates execution summary + Jenkins flags.

Does NOT modify existing Maestro YAML, ATP flows, or jenkins_atp_stage.py.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from suite.ai_module_recovery import try_ai_recovery_and_retry_module  # noqa: E402
from suite.config_loader import ModuleSpec, load_suite_config  # noqa: E402
from suite.module_runner import ModuleResult, run_module  # noqa: E402
from suite.setup_runner import run_suite_setup  # noqa: E402
from suite.summary_report import (  # noqa: E402
    build_report,
    collect_failed_module_artifacts,
    write_reports,
)


def _touch_flag(repo: Path, name: str) -> None:
    (repo / name).write_text("1\n", encoding="utf-8")


def _enabled_modules(config) -> list[ModuleSpec]:
    return [m for m in config.modules if m.enabled and m.name]


def run_complete_suite(
    repo: Path,
    *,
    app_package: str,
    maestro_cmd: str,
    config_path: Path | None = None,
    skip_setup: bool = False,
) -> int:
    config = load_suite_config(repo, config_path)
    modules = _enabled_modules(config)
    if not modules:
        print("[suite] ERROR: no enabled modules in suite config", flush=True)
        return 1

    started = time.time()
    print(f"[suite] === {config.name} ===", flush=True)
    print(f"[suite] modules={[m.name for m in modules]}", flush=True)

    if skip_setup or not config.setup_enabled:
        from suite.setup_runner import SetupResult

        setup = SetupResult(True, "setup skipped", 0.0, [])
    else:
        setup = run_suite_setup(
            repo, config, app_package=app_package, maestro_cmd=maestro_cmd
        )
        if not setup.success:
            print(f"[suite] SETUP FAILED: {setup.message}", flush=True)
            _touch_flag(repo, "suite_setup_failed.flag")
            finished = time.time()
            report = build_report(
                config,
                setup=setup,
                module_results=[],
                started_at=started,
                finished_at=finished,
            )
            write_reports(report, config)
            return 1

    results: list[ModuleResult] = []
    first_module = True
    for spec in modules:
        skip_preflight = config.skip_yaml_preflight_after_first and not first_module
        refresh = config.refresh_devices_each_module or first_module
        # Default: warm run — orchestrator skips adb pm clear (MasterSetup already ran).
        clear = config.clear_state_per_module and not first_module

        result = run_module(
            repo,
            spec,
            app_package=app_package,
            maestro_cmd=maestro_cmd,
            clear_state=clear,
            skip_yaml_preflight=skip_preflight,
            refresh_devices=refresh,
        )

        if result.status == "FAIL" and config.ai_recovery_enabled:
            print(f"[suite] AI recovery for module={spec.name!r}", flush=True)
            result = try_ai_recovery_and_retry_module(
                repo,
                spec,
                app_package=app_package,
                maestro_cmd=maestro_cmd,
                failed_result=result,
                max_attempts=config.ai_max_recovery_attempts,
            )
            if result.status == "PASS":
                print(f"[suite] AI recovery succeeded for {spec.name!r}", flush=True)

        results.append(result)
        print(
            f"[suite] module={result.name} status={result.status} "
            f"duration={result.duration_sec:.1f}s",
            flush=True,
        )

        if result.status == "FAIL":
            sid = result.suite_id
            _touch_flag(repo, f"{sid}_failed.flag")
            if not config.continue_on_failure:
                print("[suite] continue_on_failure=false — aborting suite", flush=True)
                break

        first_module = False

    # Optional retry pass for failed modules only
    if config.optional_retry_failed > 0:
        for attempt in range(1, config.optional_retry_failed + 1):
            failed_specs = [
                spec
                for spec, res in zip(modules, results)
                if res.status == "FAIL"
            ]
            if not failed_specs:
                break
            print(f"[suite] retry pass {attempt}/{config.optional_retry_failed}", flush=True)
            for spec in failed_specs:
                retry_res = run_module(
                    repo,
                    spec,
                    app_package=app_package,
                    maestro_cmd=maestro_cmd,
                    clear_state=False,
                    skip_yaml_preflight=True,
                    refresh_devices=False,
                    retry_attempt=attempt,
                )
                for i, r in enumerate(results):
                    if r.name == spec.name and r.status == "FAIL" and retry_res.status == "PASS":
                        results[i] = retry_res

    finished = time.time()
    report = build_report(
        config,
        setup=setup,
        module_results=results,
        started_at=started,
        finished_at=finished,
    )
    write_reports(report, config)

    if config.copy_failed_artifacts:
        collect_failed_module_artifacts(repo, results)

    if report.overall_status == "SUCCESS":
        return 0
    if report.overall_status == "UNSTABLE":
        _touch_flag(repo, "suite_failed.flag")
        return 2
    _touch_flag(repo, "suite_failed.flag")
    _touch_flag(repo, "suite_setup_failed.flag")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run complete ATP test suite")
    parser.add_argument("--repo", default=str(_REPO), help="Repository root")
    parser.add_argument("--app-package", default="com.kodak.steptouch")
    parser.add_argument("--maestro-cmd", default=os.environ.get("MAESTRO_CMD", "maestro.bat"))
    parser.add_argument("--config", default="", help="Path to suite_modules.yaml")
    parser.add_argument("--skip-setup", action="store_true")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    cfg = Path(args.config) if args.config else None
    return run_complete_suite(
        repo,
        app_package=args.app_package,
        maestro_cmd=args.maestro_cmd,
        config_path=cfg,
        skip_setup=args.skip_setup,
    )


if __name__ == "__main__":
    raise SystemExit(main())

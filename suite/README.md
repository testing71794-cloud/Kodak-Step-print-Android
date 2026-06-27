# Complete ATP Suite Orchestration

Runs **shared setup once**, then **all modules sequentially**, **continuing after failures**, with optional **AI Decision Engine recovery** on module failure.

## Backward compatibility

| Mode | How |
|------|-----|
| **Jenkins (default)** | Single stage `Run ATP Suite — All Modules + AI Recovery` via `jenkins_suite_stage.py` |
| **Local suite** | `scripts/run_complete_suite.bat` or `python -m suite.test_suite_runner` |
| **Single module (unchanged)** | `python scripts/jenkins_atp_stage.py all <folder> <app> <clear_state> <maestro>` |

No existing Maestro YAML, ATP flows, or `jenkins_atp_stage.py` logic is modified.

## Architecture

```
Jenkins: Run ATP Suite — All Modules + AI Recovery
    │
    ▼
jenkins_suite_stage.py  (sets ATP_AI_RECOVERY from RUN_ATP_AI_RECOVERY)
    │
    ▼
test_suite_runner.py
    ├── setup_runner.py        → MasterSetup.yaml once per device
    ├── module_runner.py       → jenkins_atp_stage.py all <folder> (CLEAR_STATE=false)
    ├── ai_module_recovery.py  → AI Decision Engine + one module retry on FAIL
    └── summary_report.py      → build-summary/suite_execution_summary.*
```

## AI recovery

When a module fails:

1. `ai_module_recovery.py` runs the AI Decision Engine (`ai/`) — screenshot, UI dump, rule-based recovery (optional OpenRouter when confidence is low).
2. The failed module is retried once via the existing `jenkins_atp_stage.py` path.
3. The suite continues to the next module regardless (unless `continue_on_failure: false`).

Control:

- Jenkins parameter **`RUN_ATP_AI_RECOVERY`** (default `true`)
- Env override **`ATP_AI_RECOVERY=0`** to disable
- Config: `suite/config/suite_modules.yaml` → `ai.enabled`, `ai.max_recovery_attempts_per_module`
- Engine rules: `ai/config/ai_engine.yaml` (`engine.enabled` must be `true` for recovery actions)

Audit trail: `ai/logs/decisions/*.jsonl` (archived by Jenkins).

## Configuration

Edit **`suite/config/suite_modules.yaml`** to add/reorder/disable modules:

```yaml
ai:
  enabled: true
  max_recovery_attempts_per_module: 2

modules:
  - name: Connection
    folder: connection
    enabled: true
```

Folder names map to `ATP TestCase Flows/<folder>/`.

## Local run

```bat
set ATP_AI_RECOVERY=1
python -m suite.test_suite_runner --repo . --app-package com.kodak.steptouch --maestro-cmd maestro.bat
```

Or:

```bat
scripts\run_complete_suite.bat
```

## Jenkins

Both **`Jenkinsfile`** and **`Jenkinsfile.hybrid.gcp-windows`** use one ATP stage after device detection:

- **Connection** and **Printing** are no longer separate Jenkins stages; they run as modules inside the suite (if enabled in `suite_modules.yaml`).
- Per-module checkbox stages (`RUN_ATP_ONBOARDING`, etc.) were removed to avoid repeated setup.

Build result:

- **SUCCESS** — all modules passed
- **UNSTABLE** — one or more module failures (default)
- **FAILURE** — master setup failed

## Performance

| Saved per suite run | How |
|---------------------|-----|
| Orchestrator `adb pm clear` between modules | `clear_state_per_module: false` |
| Repeated device refresh | `refresh_devices_before_each_module: false` |
| Repeated YAML preflight | `skip_yaml_preflight_after_first_module: true` |
| One permission/onboarding path | `MasterSetup.yaml` once |
| No duplicate Jenkins module stages | Single suite stage |

**Note:** Existing ATP wrapper YAML still uses `launchApp: clearState: true` per flow. Phase 2 (optional) can add warm-start suite wrappers without changing original flows.

## Reports

- `build-summary/suite_execution_summary.txt` — console-style summary
- `build-summary/suite_execution_summary.json` — machine-readable
- `build-summary/suite-failures/failed_modules_index.json` — failed module log paths
- Per-module reports unchanged under `reports/atp_<module>/`

## Flags

- `suite_failed.flag` — partial or total suite failure (UNSTABLE)
- `suite_setup_failed.flag` — master setup failed
- Existing `atp_<module>_failed.flag` — per failed module

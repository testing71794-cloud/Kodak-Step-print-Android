# AI Step Print Agent

Optional, **fully isolated** autonomous QA module for Kodak Step Print.

When disabled (`RUN_AI_AGENT=false` or `AI_AGENT_ENABLED=0`), the existing Maestro ATP framework is unchanged.

## Quick start

```bat
pip install -r ai-agent/requirements.txt
set OPENROUTER_API_KEY=your_key
scripts\run_ai_agent.bat assist
```

## Stateful session (QA engineer model)

The agent runs **one testing session** — not isolated cold starts per module.

1. **Single launch** — `adb pm clear` only on session cold start (first module).
2. **Warm continuation** — all subsequent modules use `clear_state=false` and `AI_AGENT_WARM_START=1`.
3. **Smart navigation** — navigates toward the next module screen instead of returning home.
4. **Adaptive waits** — polls UI until idle (no fixed 10–20s sleeps); learns timing per screen.
5. **Checkpoints** — login, printer, gallery checkpoints saved; recovery resumes from nearest checkpoint.
6. **Relaunch policy** — app restart only on crash/ANR/unrecoverable navigation.
7. **Artifact learning** — incrementally ingests status/logs/reports from prior Jenkins runs.
8. **Knowledge cache** — project scan only when repo hash changes.

## How it works (hybrid execution)

1. **Knowledge load** — cached by content hash; full rescan only when repo changes (`AI_AGENT_FORCE_RESCAN=1` to force).
2. **Fast path** — each module runs via existing `jenkins_atp_stage.py` (no Maestro YAML changes).
3. **Smart path** — on module failure only: rules → optional screenshot/UI → LLM only if still unknown.
4. **Continue on failure** — all modules in `config/modules.yaml` run sequentially.
5. **Reports always** — `AI_Agent_Report.xlsx` + `execution_summary.txt` written even on failure.

## Modes

| Mode | Behavior |
|------|----------|
| `observe` | Capture + analyze only; no taps or Maestro changes |
| `assist` | Maestro primary; AI intervenes on failure (default) |
| `autonomous` | AI drives next actions via ADB + optional Maestro |

## Jenkins

Enable parameter **`RUN_AI_AGENT`** (default **false**).

Optional stage: **AI Step Print Agent** — runs `scripts/jenkins_ai_agent_stage.py`.

## Outputs (separate from existing Excel)

| Artifact | Path |
|----------|------|
| Excel report | `ai-agent/reports/AI_Agent_Report.xlsx` |
| Dashboard | `ai-agent/reports/AI_Agent_Dashboard.html` |
| Decision log | `ai-agent/logs/decisions/decisions.jsonl` |
| Memory DB | `ai-agent/knowledge/agent_memory.db` |

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) and [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md).

## Isolation guarantee

- No edits to Maestro YAML, ATP flows, `jenkins_atp_stage.py`, or existing Excel pipeline
- New code lives under `ai-agent/` plus Jenkins entry `scripts/jenkins_ai_agent_stage.py`

# AI Decision Engine

Optional recovery layer for **Kodak Step Print** Maestro automation.  
**Does not modify** existing YAML flows, Jenkins pipelines, orchestrators, or reports.

## When it runs

| Trigger | AI runs? |
|---------|----------|
| Maestro step passes | **No** — zero interference |
| Maestro timeout / assert fail / element not found | **Yes** (if enabled) |
| `ATP_AI_RECOVERY=0` or `engine.enabled: false` | **No** — identical to today |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Maestro flow (unchanged YAML)                              │
└───────────────────────────┬─────────────────────────────────┘
                            │ failure only
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  maestro_integration.py  (opt-in wrapper)                   │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  AIDecisionEngine                                           │
│  1. ScreenAnalyzer → screenshot + uiautomator dump + OCR    │
│  2. Classify state (rules)                                  │
│  3. PopupHandler / PrinterSelector → RecoveryPlan           │
│  4. LLM advisor (optional, low confidence only)             │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  RecoveryManager → ActionExecutor (adb tap/swipe/settings)  │
│  Bounded retries → re-run Maestro → DecisionLogger          │
└─────────────────────────────────────────────────────────────┘
```

## Components

| Module | Role |
|--------|------|
| `ai_decision_engine.py` | Orchestrates classification + plan generation |
| `screen_analyzer.py` | Screenshot, UI dump, rule-based screen class |
| `ocr_engine.py` | Optional Tesseract OCR (falls back to hierarchy text) |
| `ui_parser.py` | Parse UIAutomator XML → clickable elements |
| `action_executor.py` | adb input tap/swipe, Bluetooth, app launch |
| `printer_selector.py` | Multi-printer selection from config rules |
| `popup_handler.py` | Popup pattern → dismiss / retry / fail |
| `recovery_manager.py` | Retry loop, verify recovery, logging |
| `decision_logger.py` | JSONL audit trail per decision |
| `llm_advisor.py` | Optional OpenRouter when rule confidence is low |
| `maestro_integration.py` | CLI wrapper: Maestro → AI → Maestro |
| `config/` | YAML rules (printer, popups, engine settings) |

## Quick start

```bat
pip install -r ai\requirements.txt
REM Tesseract optional: install OS binary for OCR

set ATP_AI_RECOVERY=1
python -m ai.maestro_integration ^
  --device RZCW40ZP8FX ^
  --flow "ATP TestCase Flows\connection\CO_01 - My Gallery Bluetooth Icon.yaml" ^
  --module connection ^
  --ai-recovery
```

Or:

```bat
scripts\maestro_ai_recovery_wrapper.bat RZCW40ZP8FX "ATP TestCase Flows\connection\CO_01 - My Gallery Bluetooth Icon.yaml" connection
```

## Configuration

Edit `ai/config/ai_engine.yaml`:

```yaml
engine:
  enabled: false          # default off — backward compatible

recovery:
  max_attempts: 2         # never infinite
  allow_bluetooth_enable: false
  allow_app_restart: false

permissions:
  default: allow_while_using
```

Printer priorities: `ai/config/printer_rules.yaml`  
Popup rules: `ai/config/popup_rules.yaml`

Environment overrides:

| Variable | Effect |
|----------|--------|
| `ATP_AI_RECOVERY=1` | Enable engine |
| `ATP_AI_MAX_ATTEMPTS=3` | Override retry cap |
| `ATP_AI_CONFIG=path/to/ai_engine.yaml` | Custom config |
| `OPENROUTER_API_KEY` | Optional LLM advisor |

## Decision log format

Each attempt appends one JSON line to `ai/logs/decisions/ai_decisions_YYYYMMDD.jsonl`:

```json
{
  "timestamp": "2026-06-27T10:00:00Z",
  "module_name": "connection",
  "failed_step": "Element not found: Text matching regex: Connect",
  "screen_classification": "multiple_printers",
  "confidence_score": 0.82,
  "reasoning": "Detected 4 printer-like labels",
  "action_taken": "select_printer: tap (540,960) label='Kodak Step Touch'",
  "result": "Recovered",
  "device_id": "RZCW40ZP8FX",
  "flow_path": "...",
  "attempt": 1
}
```

## Extension points

1. **Subclass `AIDecisionEngine`** and override `_module_hook()` for module-specific logic.
2. **Add popup rules** in YAML without code changes.
3. **Add printer names/serials** in `printer_rules.yaml`.
4. **Wire Jenkins optionally** (future): replace maestro invocation with wrapper via new env flag — existing `jenkins_atp_stage.py` unchanged until you opt in.

## Connection module scenarios

| Screen | Classification | Action |
|--------|----------------|--------|
| Printer not found | `printer_not_found` | Tap Search again / refresh / wait |
| Printer A,B,C,D | `multiple_printers` | Select by priority list |
| Bluetooth off | `bluetooth_disabled` | Enable BT (if config allows) → relaunch app |
| Permission sheet | `permission_dialog` | Tap configured allow option |
| Firmware / busy / paper | popup rules | dismiss / retry per YAML |

## Backward compatibility

- Default: `engine.enabled: false` and no `ATP_AI_RECOVERY`.
- Existing Maestro + Jenkins behavior is unchanged.
- All new code lives under `ai/` plus optional `scripts/maestro_ai_recovery_wrapper.bat`.

## Tests

```bat
python -m unittest ai.tests.test_ui_parser ai.tests.test_printer_selector
```

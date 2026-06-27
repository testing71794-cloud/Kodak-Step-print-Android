# AI Step Print Agent — Implementation Guide

## Step 1 — Install dependencies

```bat
cd "d:\Projects-Meastro\Kodak Step Print"
python -m venv .venv-ai-agent
.venv-ai-agent\Scripts\activate
pip install -r ai-agent/requirements.txt
```

Optional OCR on Windows: install [Tesseract](https://github.com/tesseract-ocr/tesseract) and add to PATH.

## Step 2 — Configure

Edit `ai-agent/config/agent.yaml`:
- `execution.mode`: `observe` | `assist` | `autonomous`
- `execution.max_recovery_attempts`: default 3
- `llm.model`: OpenRouter model id

Set `OPENROUTER_API_KEY` for LLM advisory when rule confidence is low.

## Step 3 — Local run

```bat
scripts\run_ai_agent.bat observe
scripts\run_ai_agent.bat assist
scripts\run_ai_agent.bat autonomous
```

First run triggers **learning phase** — scans ATP folders and builds SQLite/Chroma knowledge.

## Step 4 — Jenkins

1. Open job configuration (Script Path: `Jenkinsfile`)
2. Enable **`RUN_AI_AGENT`**
3. Choose **`AI_AGENT_MODE`**
4. Ensure `OPENROUTER_CREDENTIALS_ID` is set for LLM (optional)

When `RUN_AI_AGENT=false` (default), the new stage is skipped and behavior is identical to before.

## Step 5 — Verify outputs

After a run check:
- `ai-agent/reports/AI_Agent_Report.xlsx`
- `ai-agent/reports/AI_Agent_Dashboard.html`
- `ai-agent/logs/decisions/decisions.jsonl`
- `ai-agent/knowledge/agent_memory.db`

## Testing strategy

| Layer | Test |
|-------|------|
| Config | `python -m py_compile ai-agent/main.py` |
| Learning | Run once, verify `scan_manifest` in SQLite |
| Observe | `run_ai_agent.bat observe` — no Maestro subprocess |
| Assist | Induce Maestro failure, verify recovery log |
| Jenkins | Build with `RUN_AI_AGENT=false` then `true` |
| Isolation | Confirm no diff in Maestro YAML / ATP flows |

## Agent responsibilities

| Agent | File | Responsibility |
|-------|------|----------------|
| Planner | `agents/planner_agent.py` | Module order from knowledge |
| Execution | `agents/execution_agent.py` | Maestro subprocess |
| Vision | `agents/vision_agent.py` | Screenshot + UI dump |
| OCR | `agents/vision_agent.py` | Text extraction |
| Screen Classifier | `agents/vision_agent.py` | Screen label inference |
| Decision | `agents/decision_agent.py` | Multi-source decision + confidence |
| Recovery | `agents/decision_agent.py` | Bounded ADB recovery |
| Knowledge | `agents/knowledge_agent.py` | Project scan + KB update |
| Memory | `agents/knowledge_agent.py` | SQLite stats |
| Failure Analysis | `agents/decision_agent.py` | Root cause narrative |
| Recommendation | `agents/decision_agent.py` | Fix + priority |
| Reporting | `agents/reporting_agent.py` | Excel + dashboard |

## Retry strategy

1. Rule engine match (confidence ≥ 0.55) → execute recovery
2. Else LLM advisory (if key present)
3. Retry up to `max_recovery_attempts`
4. Log decision either way; continue session

## Troubleshooting

| Issue | Action |
|-------|--------|
| No devices | Run device detection first; check `detected_devices.txt` |
| Empty OCR | Install Tesseract or rely on UIAutomator text |
| LangGraph import error | Sequential fallback runs automatically |
| LLM timeout | Increase `llm.timeout_sec` in config |

## Extension for new applications

1. Copy `config/app_kodak_step_print.yaml` → `config/app_<id>.yaml`
2. Update workflows, popups, business_rules
3. Set `agent.app_id` in `agent.yaml`

Core agents, graph, memory, and reporting remain unchanged.

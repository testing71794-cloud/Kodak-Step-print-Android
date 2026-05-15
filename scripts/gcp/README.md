# GCP orchestrator scripts (Linux)

Used by **opt-in** `Jenkinsfile.hybrid.gcp-windows` — not the default `Jenkinsfile`.

| Script | Role |
|--------|------|
| `jenkins_ci_install.sh` | pip install `scripts/requirements-python.txt` on GCP |
| `jenkins_ci_post_reports.sh` | Excel merge, build summary, `execution_logs.zip` |
| `jenkins_ci_send_email.sh` | Email via venv Python (hybrid GCP stage) |
| `_venv.sh` | Persistent venv helper (PEP 668 safe) |

**Ubuntu agent (recommended):** install once per machine:

```bash
sudo apt install -y python3.12-venv python3-pip
# or: sudo apt install -y python3-venv
```

If `python3-venv` is missing, scripts fall back to `pip install --user` with `PIP_BREAK_SYSTEM_PACKAGES` (set `JENKINS_ORCHESTRATOR_ALLOW_USER_PIP=0` to fail instead).

**Venv path (default):** `$HOME/jenkins-venvs/kodak-atp-orchestrator` — override with `JENKINS_ORCHESTRATOR_VENV`.

**Windows device agent** uses `scripts/jenkins_ci_install_windows_device.bat` (pip only, no npm).

See `docs/DISTRIBUTED_GCP_WINDOWS_ARCHITECTURE.md` for full migration plan.

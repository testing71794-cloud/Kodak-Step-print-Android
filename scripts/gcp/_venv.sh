#!/usr/bin/env bash
# Shared venv for GCP orchestrator (PEP 668 / externally-managed-environment safe).
# Persistent on the agent so later stages survive workspace deleteDir + unstash.
resolve_gcp_python() {
  local ROOT="${1:-.}"
  local VENV_DIR="${JENKINS_ORCHESTRATOR_VENV:-${HOME}/jenkins-venvs/kodak-atp-orchestrator}"
  mkdir -p "$(dirname "$VENV_DIR")"

  local PY_BOOT="${PYTHON_BOOT:-}"
  if [[ -z "$PY_BOOT" ]]; then
    for c in python3.13 python3.12 python3.11 python3; do
      if command -v "$c" >/dev/null 2>&1; then PY_BOOT="$(command -v "$c")"; break; fi
    done
  fi
  if [[ -z "$PY_BOOT" ]]; then
    echo "[gcp-venv] ERROR: python3 not found (install python3-venv on the agent)"
    return 1
  fi

  if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "[gcp-venv] creating venv at $VENV_DIR (boot=$PY_BOOT)"
    if ! "$PY_BOOT" -m venv "$VENV_DIR" 2>/dev/null; then
      echo "[gcp-venv] ERROR: python3 -m venv failed. On Ubuntu run: sudo apt install -y python3-venv python3-pip"
      return 1
    fi
  fi

  export PY="$VENV_DIR/bin/python"
  export PIP="$VENV_DIR/bin/pip"
  echo "[gcp-venv] Using PY=$PY"

  "$PY" -m pip install --upgrade pip --quiet
  "$PY" -m pip install -r "$ROOT/scripts/requirements-python.txt" --quiet
  return 0
}

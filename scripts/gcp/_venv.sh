#!/usr/bin/env bash
# Shared venv for GCP orchestrator (PEP 668 / externally-managed-environment safe).
# Persistent on the agent so later stages survive workspace deleteDir + unstash.
#
# Preferred: python3-venv (e.g. sudo apt install -y python3.12-venv)
# Fallback: pip install virtualenv, then pip --user with PIP_BREAK_SYSTEM_PACKAGES.

_gcp_python_minor_version() {
  "$1" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'
}

_gcp_can_import_venv() {
  "$1" -c 'import venv' >/dev/null 2>&1
}

_gcp_apt_venv_pkg_status() {
  local PY_MINOR="$1"
  if ! command -v dpkg >/dev/null 2>&1; then
    echo "unknown (dpkg not available)"
    return 0
  fi
  if dpkg -s "python${PY_MINOR}-venv" >/dev/null 2>&1; then
    echo "installed (python${PY_MINOR}-venv)"
    return 0
  fi
  if dpkg -s python3-venv >/dev/null 2>&1; then
    echo "installed (python3-venv)"
    return 0
  fi
  echo "not installed (try: sudo apt install -y python${PY_MINOR}-venv python3-pip)"
}

_gcp_log_venv_log() {
  local VENV_LOG="$1"
  if [[ -f "$VENV_LOG" && -s "$VENV_LOG" ]]; then
    echo "[gcp-venv] venv command output:" >&2
    sed 's/^/[gcp-venv]   /' "$VENV_LOG" >&2 || cat "$VENV_LOG" >&2
  fi
}

_gcp_try_pip_install_virtualenv() {
  local PY_BOOT="$1"
  echo "[gcp-venv] attempting to install virtualenv via pip for $PY_BOOT"
  if "$PY_BOOT" -m pip install --user --upgrade virtualenv --quiet 2>/dev/null; then
    echo "[gcp-venv] installed virtualenv into user site-packages"
    return 0
  fi
  if PIP_BREAK_SYSTEM_PACKAGES=1 "$PY_BOOT" -m pip install --user --upgrade virtualenv --quiet 2>/dev/null; then
    echo "[gcp-venv] installed virtualenv into user site-packages (break-system-packages)"
    return 0
  fi
  if "$PY_BOOT" -m pip install --upgrade virtualenv --quiet 2>/dev/null; then
    echo "[gcp-venv] installed virtualenv into system/python environment"
    return 0
  fi
  if PIP_BREAK_SYSTEM_PACKAGES=1 "$PY_BOOT" -m pip install --upgrade virtualenv --quiet 2>/dev/null; then
    echo "[gcp-venv] installed virtualenv (break-system-packages)"
    return 0
  fi
  echo "[gcp-venv] WARN: could not install virtualenv via pip"
  return 1
}

_gcp_pip_user_install() {
  local PY_BOOT="$1"
  local ROOT="$2"
  export GCP_PYTHON_MODE="${GCP_PYTHON_MODE:-user}"
  export PY="$PY_BOOT"
  export PATH="${HOME}/.local/bin:${PATH}"
  export PIP_BREAK_SYSTEM_PACKAGES=1
  echo "[gcp-venv] Using PY=$PY (user site-packages; not isolated venv)"
  if ! "$PY" -m pip install --user --upgrade pip --quiet 2>/dev/null; then
    "$PY" -m pip install --user --upgrade pip --break-system-packages --quiet
  fi
  if ! "$PY" -m pip install --user -r "$ROOT/scripts/requirements-python.txt" --quiet 2>/dev/null; then
    "$PY" -m pip install --user -r "$ROOT/scripts/requirements-python.txt" --break-system-packages --quiet
  fi
}

_gcp_venv_has_pip() {
  local PY_VENV="$1"
  "$PY_VENV" -m pip --version >/dev/null 2>&1
}

_gcp_repair_venv_pip() {
  local PY_VENV="$1"
  echo "[gcp-venv] bootstrapping pip in existing venv ($PY_VENV)"
  if "$PY_VENV" -m ensurepip --upgrade >/dev/null 2>&1 && _gcp_venv_has_pip "$PY_VENV"; then
    return 0
  fi
  if "$PY_VENV" -m ensurepip >/dev/null 2>&1 && _gcp_venv_has_pip "$PY_VENV"; then
    return 0
  fi
  return 1
}

_gcp_venv_pip_install() {
  local PY_VENV="$1"
  local ROOT="$2"
  if ! _gcp_venv_has_pip "$PY_VENV"; then
    echo "[gcp-venv] ERROR: venv python has no pip: $PY_VENV" >&2
    return 1
  fi
  export GCP_PYTHON_MODE="${GCP_PYTHON_MODE:-venv}"
  export PY="$PY_VENV"
  export PIP="${PY_VENV%/python}/pip"
  echo "[gcp-venv] Using PY=$PY (venv)"
  "$PY" -m pip install --upgrade pip --quiet
  "$PY" -m pip install -r "$ROOT/scripts/requirements-python.txt" --quiet
}

_gcp_try_create_stdlib_venv() {
  local PY_BOOT="$1"
  local VENV_DIR="$2"
  local VENV_LOG="$3"
  echo "[gcp-venv] trying: $PY_BOOT -m venv $VENV_DIR"
  if "$PY_BOOT" -m venv "$VENV_DIR" >"$VENV_LOG" 2>&1 && [[ -x "$VENV_DIR/bin/python" ]]; then
    return 0
  fi
  _gcp_log_venv_log "$VENV_LOG"
  return 1
}

_gcp_try_create_virtualenv_venv() {
  local PY_BOOT="$1"
  local VENV_DIR="$2"
  local VENV_LOG="$3"
  if ! "$PY_BOOT" -m virtualenv --version >/dev/null 2>&1; then
    _gcp_try_pip_install_virtualenv "$PY_BOOT" || true
  fi
  if ! "$PY_BOOT" -m virtualenv --version >/dev/null 2>&1; then
    echo "[gcp-venv] virtualenv module still unavailable after pip install attempt"
    return 1
  fi
  echo "[gcp-venv] trying: $PY_BOOT -m virtualenv $VENV_DIR"
  if "$PY_BOOT" -m virtualenv "$VENV_DIR" >"$VENV_LOG" 2>&1 && [[ -x "$VENV_DIR/bin/python" ]]; then
    echo "[gcp-venv] created venv via python -m virtualenv"
    return 0
  fi
  _gcp_log_venv_log "$VENV_LOG"
  return 1
}

_gcp_finalize_new_venv() {
  local VENV_DIR="$1"
  local ROOT="$2"
  local PY_NEW="$VENV_DIR/bin/python"
  if ! _gcp_venv_has_pip "$PY_NEW"; then
    _gcp_repair_venv_pip "$PY_NEW" || true
  fi
  if _gcp_venv_has_pip "$PY_NEW"; then
    _gcp_venv_pip_install "$PY_NEW" "$ROOT"
    return 0
  fi
  echo "[gcp-venv] WARN: new venv still has no pip; removing $VENV_DIR"
  rm -rf "$VENV_DIR"
  return 1
}

_gcp_try_apt_install_python_venv() {
  local PY_MINOR="$1"
  if ! command -v sudo >/dev/null 2>&1; then
    echo "[gcp-venv] WARN: sudo not found; cannot install python${PY_MINOR}-venv via apt"
    return 1
  fi
  if ! sudo -n true >/dev/null 2>&1; then
    echo "[gcp-venv] WARN: sudo not available without password; cannot install python${PY_MINOR}-venv"
    return 1
  fi
  echo "[gcp-venv] attempting: sudo apt-get install -y python${PY_MINOR}-venv python3-venv python3-pip"
  sudo apt-get update -qq >/dev/null 2>&1 || true
  if sudo apt-get install -y "python${PY_MINOR}-venv" python3-venv python3-pip >/dev/null 2>&1; then
    echo "[gcp-venv] installed python${PY_MINOR}-venv via apt"
    return 0
  fi
  echo "[gcp-venv] WARN: apt install python${PY_MINOR}-venv failed"
  return 1
}

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
    echo "[gcp-venv] ERROR: python3 not found"
    return 1
  fi

  local PY_MINOR
  PY_MINOR="$(_gcp_python_minor_version "$PY_BOOT")"
  echo "[gcp-venv] boot python: $PY_BOOT (minor=$PY_MINOR)"
  if _gcp_can_import_venv "$PY_BOOT"; then
    echo "[gcp-venv] stdlib venv module: available"
  else
    echo "[gcp-venv] stdlib venv module: NOT available"
  fi
  echo "[gcp-venv] apt python venv package: $(_gcp_apt_venv_pkg_status "$PY_MINOR")"

  # Reuse existing venv only when pip is usable (broken venvs lack ensurepip without python*-venv)
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    local PY_VENV="$VENV_DIR/bin/python"
    if _gcp_venv_has_pip "$PY_VENV"; then
      _gcp_venv_pip_install "$PY_VENV" "$ROOT"
      return 0
    fi
    echo "[gcp-venv] WARN: venv at $VENV_DIR exists but pip is missing"
    if _gcp_repair_venv_pip "$PY_VENV"; then
      _gcp_venv_pip_install "$PY_VENV" "$ROOT"
      return 0
    fi
    echo "[gcp-venv] removing broken venv (no pip) at $VENV_DIR"
    rm -rf "$VENV_DIR"
  elif [[ -d "$VENV_DIR" ]]; then
    echo "[gcp-venv] removing incomplete venv at $VENV_DIR"
    rm -rf "$VENV_DIR"
  fi

  local VENV_LOG
  VENV_LOG="$(mktemp)"
  trap 'rm -f "$VENV_LOG"' RETURN

  echo "[gcp-venv] creating venv at $VENV_DIR"
  if _gcp_try_create_stdlib_venv "$PY_BOOT" "$VENV_DIR" "$VENV_LOG"; then
    _gcp_finalize_new_venv "$VENV_DIR" "$ROOT" && return 0
  fi

  local NEED_APT=0
  if ! _gcp_can_import_venv "$PY_BOOT"; then
    NEED_APT=1
  elif grep -qiE 'ensurepip|venv.*no module|No module named' "$VENV_LOG" 2>/dev/null; then
    NEED_APT=1
  fi

  if [[ "$NEED_APT" == "1" ]]; then
    if _gcp_try_apt_install_python_venv "$PY_MINOR"; then
      if _gcp_try_create_stdlib_venv "$PY_BOOT" "$VENV_DIR" "$VENV_LOG"; then
        _gcp_finalize_new_venv "$VENV_DIR" "$ROOT" && return 0
      fi
    fi
  fi

  if _gcp_try_create_virtualenv_venv "$PY_BOOT" "$VENV_DIR" "$VENV_LOG"; then
    _gcp_finalize_new_venv "$VENV_DIR" "$ROOT" && return 0
  fi

  _gcp_log_venv_log "$VENV_LOG"
  echo "[gcp-venv] ERROR: could not create venv." >&2
  echo "[gcp-venv] On Ubuntu/Debian install (as root on the agent):" >&2
  echo "  sudo apt install -y python${PY_MINOR}-venv python3-pip" >&2
  echo "  # or: sudo apt install -y python3-venv" >&2

  if [[ "${JENKINS_ORCHESTRATOR_ALLOW_USER_PIP:-1}" == "0" ]]; then
    echo "[gcp-venv] WARN: venv creation failed and user-pip fallback disabled; using boot python" >&2
    export GCP_PYTHON_MODE="${GCP_PYTHON_MODE:-system}"
    export PY="$PY_BOOT"
    return 0
  fi

  echo "[gcp-venv] WARN: falling back to pip --user (install python${PY_MINOR}-venv when possible)" >&2
  _gcp_pip_user_install "$PY_BOOT" "$ROOT"
  return 0
}

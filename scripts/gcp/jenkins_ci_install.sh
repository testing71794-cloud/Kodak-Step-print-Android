#!/usr/bin/env bash
# GCP orchestrator agent: Python dependencies for report/AI orchestration only.
# Uses a persistent venv (PEP 668 safe). Does NOT install Maestro, Android SDK, or Node.
set -euo pipefail
ROOT="${1:?Usage: jenkins_ci_install.sh <repo-root>}"
cd "$ROOT"
export JENKINS_WORKLOAD_PROFILE="${JENKINS_WORKLOAD_PROFILE:-gcp-orchestrator}"
echo "[workload] profile=${JENKINS_WORKLOAD_PROFILE} scope=gcp-orchestrator"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_venv.sh
source "$SCRIPT_DIR/_venv.sh"
resolve_gcp_python "$ROOT"
mkdir -p build-summary
echo "[gcp-install] done (venv ready; no Maestro/ADB on GCP orchestrator)"

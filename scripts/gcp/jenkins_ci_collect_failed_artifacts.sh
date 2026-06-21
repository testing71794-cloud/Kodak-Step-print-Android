#!/usr/bin/env bash
# Collect failed Maestro logs/videos into build-summary/failed_tests_artifacts.zip
set -euo pipefail
ROOT="${1:?Usage: jenkins_ci_collect_failed_artifacts.sh <repo-root>}"
cd "$ROOT"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_venv.sh
source "$SCRIPT_DIR/_venv.sh"
resolve_gcp_python "$ROOT"
echo "[gcp-failed-artifacts] running collect_failed_artifacts.py"
"$PY" scripts/collect_failed_artifacts.py "$ROOT"

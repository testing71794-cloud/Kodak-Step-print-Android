#!/usr/bin/env bash
# Send final execution email (failed tests only; Gmail size-safe attachments).
set -euo pipefail
ROOT="${1:?Usage: jenkins_ci_send_email.sh <repo-root>}"
cd "$ROOT"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_venv.sh
source "$SCRIPT_DIR/_venv.sh"
if ! resolve_gcp_python "$ROOT"; then
  echo "[gcp-email] WARN: resolve_gcp_python failed; using boot python for send_email.py"
  export PY="${PYTHON_BOOT:-python3}"
elif [[ -z "${PY:-}" ]]; then
  echo "[gcp-email] WARN: PY not set after resolve_gcp_python; using boot python"
  export PY="${PYTHON_BOOT:-python3}"
else
  echo "[gcp-email] Python mode: ${GCP_PYTHON_MODE:-unknown} PY=$PY"
fi

if [[ -n "${BRANCH_NAME:-}" && -z "${ATP_GIT_BRANCH:-}" ]]; then
  export ATP_GIT_BRANCH="$BRANCH_NAME"
fi
if [[ -n "${GIT_BRANCH:-}" && -z "${ATP_GIT_BRANCH:-}" ]]; then
  export ATP_GIT_BRANCH="$GIT_BRANCH"
fi
if [[ -n "${BUILD_URL:-}" ]]; then
  export BUILD_URL
fi
if [[ -n "${BUILD_NUMBER:-}" ]]; then
  export BUILD_NUMBER
fi

ZIP_PATH="build-summary/failed_tests_artifacts.zip"
if [[ -f "$ZIP_PATH" ]]; then
  ZIP_BYTES=$(wc -c <"$ZIP_PATH" | tr -d ' ')
  echo "[gcp-email] ZIP Size: ${ZIP_BYTES} bytes ($ZIP_PATH)"
else
  echo "[gcp-email] ZIP Size: 0 (no failed_tests_artifacts.zip)"
fi

if [[ -f "build-summary/failed_tests_summary.json" ]]; then
  FAILED_CT=$("$PY" -c "import json; d=json.load(open('build-summary/failed_tests_summary.json')); print(d.get('failed_count', len(d.get('failures', []))))" 2>/dev/null || echo "?")
  echo "[gcp-email] Failed Tests Count: ${FAILED_CT}"
fi

echo "[gcp-email] Artifact URL: ${BUILD_URL:-}(not set)artifact/build-summary/failed_tests_artifacts.zip"
echo "[gcp-email] Running mailout/send_email.py"
"$PY" mailout/send_email.py || echo 1 >email_failed.flag

#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:?Usage: jenkins_ci_send_email.sh <repo-root>}"
cd "$ROOT"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_venv.sh
source "$SCRIPT_DIR/_venv.sh"
resolve_gcp_python "$ROOT"
echo "[gcp-email] Running mailout/send_email.py"
"$PY" mailout/send_email.py || echo 1 >email_failed.flag

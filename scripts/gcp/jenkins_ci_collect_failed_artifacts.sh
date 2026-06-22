#!/usr/bin/env bash
# Collect failed Maestro logs/screenshots/videos into build-summary/failed_tests_artifacts.zip
set -euo pipefail
ROOT="${1:?Usage: jenkins_ci_collect_failed_artifacts.sh <repo-root>}"
cd "$ROOT"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_venv.sh
source "$SCRIPT_DIR/_venv.sh"
resolve_gcp_python "$ROOT" || {
  echo "[gcp-failed-artifacts] WARN: venv bootstrap failed; using system python"
  PY="${PYTHON_BOOT:-python3}"
}

if command -v ffmpeg >/dev/null 2>&1; then
  echo "[gcp-failed-artifacts] ffmpeg available for video compression"
else
  echo "[gcp-failed-artifacts] WARN: ffmpeg not in PATH; failure videos may remain large"
fi

echo "[gcp-failed-artifacts] running collect_failed_artifacts.py"
"$PY" scripts/collect_failed_artifacts.py "$ROOT"

if [[ -f build-summary/failed_tests_artifacts.zip ]]; then
  echo "[gcp-failed-artifacts] ZIP Size: $(wc -c <build-summary/failed_tests_artifacts.zip | tr -d ' ') bytes"
fi
if [[ -f build-summary/failed_tests_summary.json ]]; then
  "$PY" -c "
import json
from pathlib import Path
d = json.loads(Path('build-summary/failed_tests_summary.json').read_text())
print('[gcp-failed-artifacts] Failed Tests Count:', d.get('failed_count', 0))
print('[gcp-failed-artifacts] Videos Attached:', d.get('videos_attached', 0))
print('[gcp-failed-artifacts] Screenshots Attached:', d.get('screenshots_attached', 0))
" 2>/dev/null || true
fi

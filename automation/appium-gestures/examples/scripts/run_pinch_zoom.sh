#!/usr/bin/env bash
# Optional Maestro hook — COPY to your flows folder if you choose Option A.
# Does NOT run unless you add runScript to a flow yourself.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

GESTURE="${1:-both}"
UDID="${2:-${ANDROID_SERIAL:-}}"

cd "${MODULE_DIR}"
ARGS=("${GESTURE}")
if [[ -n "${UDID}" ]]; then
  ARGS+=("--udid" "${UDID}")
fi

mvn -q exec:java -Dexec.args="${ARGS[*]}"
echo "Pinch gesture OK"

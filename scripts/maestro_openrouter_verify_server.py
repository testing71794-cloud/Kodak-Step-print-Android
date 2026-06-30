#!/usr/bin/env python3
"""Local HTTP helper for Maestro Studio OpenRouter vision checks.

Start before Studio runs (no GraalJS file access needed):
  py scripts/maestro_openrouter_verify_server.py
"""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from verify_ga02_3x3_grid_ai import verify_basename  # noqa: E402

_HOST = "127.0.0.1"
_PORT = 8765


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_POST(self) -> None:
        if self.path != "/verify/ga02_3x3":
            self.send_error(404, "Use POST /verify/ga02_3x3")
            return
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON body")
            return
        name = (body.get("screenshot_basename") or "GA_02_3x3_grid_verify").strip()
        use_adb = body.get("use_adb", True)
        if isinstance(use_adb, str):
            use_adb = use_adb.lower() not in {"0", "false", "no"}
        result = verify_basename(name, use_adb=bool(use_adb))
        payload = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> int:
    server = HTTPServer((_HOST, _PORT), _Handler)
    print(f"Maestro OpenRouter verify server listening on http://{_HOST}:{_PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

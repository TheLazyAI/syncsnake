#!/usr/bin/env python3
"""
serve_deck.py — serve the SyncSnake swipe deck with a live Refresh endpoint.

Serves this directory over HTTP and adds one API route:

    GET /api/refresh   -> regenerates cards from the agent's catalogue.json
                          (via build_records.build()), rewrites records.js,
                          and returns the fresh cards as JSON.

The deck's Refresh button calls this. Opening the deck via file:// works too,
but the button only does anything when the page is served from here (a browser
button can't run Python on its own).

Usage:
    /Users/maryann/sonic/.venv/bin/python serve_deck.py        # http://localhost:8000/app.html
    PORT=9000 python serve_deck.py                              # custom port
"""

import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DECK_DIR = Path(__file__).parent
PORT = int(os.environ.get("PORT", "8000"))

# Import the generator from the agent project.
sys.path.insert(0, "/Users/maryann/sync_licensing_agent")
import build_records  # noqa: E402


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(DECK_DIR), **kw)

    def do_GET(self):
        if self.path.split("?")[0].rstrip("/") == "/api/refresh":
            return self._refresh()
        return super().do_GET()

    def _refresh(self):
        try:
            records = build_records.build()          # read catalogue.json -> cards
            build_records.main()                     # also rewrite records.js on disk
            payload = json.dumps(records, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            print(f"  /api/refresh -> {len(records)} cards")
        except Exception as e:  # surface the error to the browser console
            msg = json.dumps({"error": str(e)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(msg)
            print(f"  /api/refresh FAILED: {e}")


def main():
    os.chdir(DECK_DIR)
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"SyncSnake deck → http://localhost:{PORT}/app.html")
    print(f"Refresh endpoint → http://localhost:{PORT}/api/refresh")
    print("Ctrl-C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()

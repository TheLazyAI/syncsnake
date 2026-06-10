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

# Import the generator + feedback store from the agent project.
sys.path.insert(0, "/Users/maryann/sync_licensing_agent")
import build_records   # noqa: E402
import feedback_store  # noqa: E402


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(DECK_DIR), **kw)

    def _route(self):
        return self.path.split("?")[0].rstrip("/")

    def _send_json(self, obj, code=200):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except Exception:
            return {}

    def do_GET(self):
        route = self._route()
        if route == "/api/refresh":
            return self._refresh()
        if route == "/api/feedback":
            return self._send_json({"flags": feedback_store.load_flags()})
        return super().do_GET()

    def do_POST(self):
        if self._route() == "/api/feedback":
            return self._add_feedback()
        return self._send_json({"error": "not found"}, 404)

    def do_DELETE(self):
        if self._route() == "/api/feedback":
            return self._remove_feedback()
        return self._send_json({"error": "not found"}, 404)

    def _add_feedback(self):
        body = self._read_body()
        try:
            rec = feedback_store.add_flag(
                cat=body["cat"], title=body["title"],
                reason=body["reason"], note=body.get("note", ""))
            print(f"  /api/feedback +{rec['reason']} -> {rec['id']}")
            self._send_json({"ok": True, "flag": rec})
        except Exception as e:
            self._send_json({"error": str(e)}, 400)
            print(f"  /api/feedback FAILED: {e}")

    def _remove_feedback(self):
        body = self._read_body()
        fid = body.get("id", "")
        removed = feedback_store.remove_flag(fid)
        print(f"  /api/feedback -unflag {fid} ({'ok' if removed else 'missing'})")
        self._send_json({"ok": removed, "id": fid})

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

#!/usr/bin/env python3
"""Local proxy for the GeM bids API.

Run:
    python3 gem_proxy.py

Then open the UI (index.html on GitHub Pages or locally), and use the
bookmarklet on bidplus.gem.gov.in to send your session tokens here.
"""

import datetime
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 7432
GEM_URL = "https://bidplus.gem.gov.in/all-bids-data"

TOKENS = {"cookies": "", "csrf": "", "csrt": "", "saved_at": ""}


def _success_page(csrf, cookies):
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Tokens saved</title>
<style>
  body {{ font-family: -apple-system, sans-serif; background: #0f1115; color: #e6e9ef;
         display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
  .card {{ background: #161a22; border: 1px solid #2a2f3a; border-radius: 12px;
           padding: 28px 36px; text-align: center; max-width: 460px; }}
  .ok {{ color: #3ecf8e; font-size: 48px; margin: 0 0 12px; }}
  h1 {{ margin: 0 0 8px; font-size: 18px; }}
  p {{ color: #8b93a7; margin: 6px 0; font-size: 13px; }}
  code {{ background: #1d222c; padding: 2px 6px; border-radius: 4px; font-size: 12px; }}
</style></head>
<body>
  <div class="card">
    <div class="ok">&#10003;</div>
    <h1>Tokens saved to local proxy</h1>
    <p>CSRF token: <code>{len(csrf)} chars</code> &middot; Cookies: <code>{len(cookies)} chars</code></p>
    <p>You can close this tab. Switch back to the GeM Bid Explorer UI &mdash; the status dot should now be green.</p>
    <p style="margin-top:18px;font-size:11px;">This tab will auto-close in 3 seconds.</p>
  </div>
  <script>setTimeout(function(){{ window.close(); }}, 3000);</script>
</body></html>"""


def _cors(handler):
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")


def _json(handler, status, payload):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    _cors(handler)
    handler.end_headers()
    handler.wfile.write(body)


def _csrf_cookie_value(cookies):
    m = re.search(r"csrf_gem_cookie=([^;]+)", cookies)
    return m.group(1) if m else ""


def _fetch_gem(filters, start):
    if not TOKENS["cookies"] or not TOKENS["csrf"]:
        return 401, {"error": "No tokens stored. Click the bookmarklet on the GeM page first."}

    csrf = TOKENS["csrf"]
    cookie_csrf = _csrf_cookie_value(TOKENS["cookies"])
    csrt = TOKENS["csrt"] or csrf[:16]

    payload_obj = {
        "param": {
            "searchBid": filters.get("searchBid", ""),
            "searchType": "fullText",
        },
        "filter": {
            "bidStatusType": filters.get("bidStatusType", "bidrastatus"),
            "byType": filters.get("byType", "all"),
            "highBidValue": filters.get("highBidValue", ""),
            "byEndDate": {
                "from": filters.get("dateFrom", ""),
                "to": filters.get("dateTo", ""),
            },
            "sort": filters.get("sort", "Bid-End-Date-Latest"),
            "byStatus": filters.get("byStatus", ""),
        },
    }

    form = urllib.parse.urlencode({
        "payload": json.dumps(payload_obj, separators=(",", ":")),
        "csrf_bd_gem_nk": cookie_csrf,
        "start": str(start),
    }).encode("utf-8")

    url = f"{GEM_URL}?csrt={csrt}"
    req = urllib.request.Request(url, data=form, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
    req.add_header("X-Requested-With", "XMLHttpRequest")
    req.add_header("X-TS-AJAX-Request", "true")
    req.add_header("X-Security-CSRF-Token", csrf)
    req.add_header("Cookie", TOKENS["cookies"])
    req.add_header("Referer", "https://bidplus.gem.gov.in/all-bids")
    req.add_header("Origin", "https://bidplus.gem.gov.in")
    req.add_header(
        "User-Agent",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    )

    print(f"[proxy] -> POST {url}", flush=True)
    print(f"[proxy]    csrf header: {csrf[:20]}... ({len(csrf)} chars)", flush=True)
    print(f"[proxy]    cookie csrf_bd_gem_nk: {cookie_csrf[:20]}... ({len(cookie_csrf)} chars)", flush=True)
    print(f"[proxy]    cookie length: {len(TOKENS['cookies'])} chars", flush=True)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            print(f"[proxy] <- 200 OK ({len(body)} bytes)", flush=True)
            return 200, json.loads(body)
    except urllib.error.HTTPError as e:
        snippet = e.read().decode("utf-8", errors="replace")[:1500]
        print(f"[proxy] <- {e.code} {e.reason}", flush=True)
        print(f"[proxy]    body: {snippet[:500]}", flush=True)
        return e.code, {"error": f"GeM responded {e.code}", "body": snippet}
    except Exception as e:
        print(f"[proxy] <- ERR: {e}", flush=True)
        return 502, {"error": f"Proxy error: {e}"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 - signature comes from base class
        print(f"[proxy] {self.address_string()} - {format % args}")

    def do_OPTIONS(self):
        self.send_response(204)
        _cors(self)
        self.end_headers()

    def do_GET(self):
        if self.path == "/ping":
            _json(self, 200, {"ok": True, "has_tokens": bool(TOKENS["cookies"] and TOKENS["csrf"])})
        elif self.path == "/get-tokens":
            _json(self, 200, {
                "cookies": TOKENS["cookies"],
                "csrf": TOKENS["csrf"],
                "csrt": TOKENS["csrt"],
                "saved_at": TOKENS["saved_at"],
            })
        else:
            _json(self, 404, {"error": "Not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b""

        # Form-encoded path: used by the bookmarklet (CSP-safe form submission).
        if self.path == "/save-tokens-form":
            try:
                form = urllib.parse.parse_qs(raw.decode("utf-8"))
            except UnicodeDecodeError:
                self._send_html(400, "<h1>Bad request</h1>")
                return
            cookies = form.get("cookies", [""])[0]
            csrf = form.get("csrf", [""])[0]
            TOKENS["cookies"] = cookies
            TOKENS["csrf"] = csrf
            TOKENS["saved_at"] = datetime.datetime.now().isoformat(timespec="seconds")
            print(f"[proxy] tokens saved via form (csrf {len(csrf)} chars, cookies {len(cookies)} chars)")
            self._send_html(200, _success_page(csrf, cookies))
            return

        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError:
            _json(self, 400, {"error": "Invalid JSON"})
            return

        if self.path == "/save-tokens":
            TOKENS["cookies"] = body.get("cookies", "")
            TOKENS["csrf"] = body.get("csrf", "")
            TOKENS["csrt"] = body.get("csrt", "")
            TOKENS["saved_at"] = datetime.datetime.now().isoformat(timespec="seconds")
            print(f"[proxy] tokens saved via json (csrf {len(TOKENS['csrf'])} chars, cookies {len(TOKENS['cookies'])} chars, csrt {len(TOKENS['csrt'])} chars)")
            _json(self, 200, {"ok": True, "saved_at": TOKENS["saved_at"]})
        elif self.path == "/gem-proxy":
            filters = body.get("filters", {})
            start = int(body.get("start", 0))
            status, data = _fetch_gem(filters, start)
            _json(self, status, data)
        else:
            _json(self, 404, {"error": "Not found"})

    def _send_html(self, status, html):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        _cors(self)
        self.end_headers()
        self.wfile.write(body)


def main():
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[proxy] listening on http://127.0.0.1:{PORT}")
    print("[proxy] next: open the UI and click the bookmarklet on bidplus.gem.gov.in")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[proxy] shutting down")


if __name__ == "__main__":
    main()

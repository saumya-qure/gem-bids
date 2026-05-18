# GeM Bid Explorer

A lightweight tool to fetch, filter, and export bids from the
Government e-Marketplace ([bidplus.gem.gov.in](https://bidplus.gem.gov.in)).

GeM has no public API, blocks direct browser requests, and sets its session
cookies as HttpOnly (so JavaScript can't read them). This tool works around
that with a small local proxy plus a one-time copy of a real network request
from DevTools. Your tokens never leave your machine.

## How it works

```
[DevTools Network → Copy as cURL] ──▶ [UI parses headers] ──▶ [gem_proxy.py] ──▶ [GeM API]
                                                                    ▲
                                                    [index.html in your browser]
```

- **`index.html`** — the UI. Hosted on GitHub Pages; runs entirely in your browser.
- **`gem_proxy.py`** — a Python 3 script you run locally. Holds your session
  tokens in memory and forwards requests to GeM.

## Setup (one time)

You need Python 3 installed (any version ≥ 3.8 — comes with macOS by default).

1. **Clone or download this repo.**
   ```bash
   git clone https://github.com/saumya-qure/gem-bids.git
   cd gem-bids
   ```

2. **Start the proxy:**
   ```bash
   python3 gem_proxy.py
   ```
   You should see `[proxy] listening on http://127.0.0.1:7432`.
   Leave this terminal running.

3. **Open the UI:** [https://saumya-qure.github.io/gem-bids/](https://saumya-qure.github.io/gem-bids/)
   (or run it locally with `python3 -m http.server 8000` and visit
   `http://localhost:8000/index.html`).

## Loading tokens (every few hours)

1. Open [bidplus.gem.gov.in/all-bids](https://bidplus.gem.gov.in/all-bids) and log in if needed.
2. Open DevTools (`Cmd+Option+I` on macOS) → **Network** tab.
3. Filter for `all-bids-data`. Change any filter or click "Search" on GeM to
   fire a real request. A row appears in Network.
4. Right-click the row → **Copy** → **Copy as cURL (bash)**.
5. Paste into the **Setup** section of the UI → click **Load tokens**. The
   status dot turns green.

When tokens expire (Fetch returns 401/403), repeat steps 1–5.

## Daily use

1. With the proxy running and tokens loaded, set your **API filters** (search
   text, status, type, date range, etc.) and click **Fetch bids**.
2. Use the **Advanced Filters** (ministry, department, category, free-text)
   to narrow the fetched set, sort by any column, and export to CSV.

## Two layers of filtering

- **API filters** — sent to GeM as part of the request. Use these to narrow
  what gets pulled. The API returns 10 results per page; the "Max pages"
  field controls how many pages to fetch.
- **Advanced filters** — applied client-side on the already-fetched results.
  Use these for quick slicing without re-hitting the API.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Red dot, "Proxy not running" | The Python script isn't running. Run `python3 gem_proxy.py`. |
| Orange dot, "no tokens" | Paste a fresh cURL from DevTools (see "Loading tokens" above). |
| `GeM responded 403` after fetch | Tokens expired — paste a fresh cURL. |
| `No X-Security-CSRF-Token header found` | You copied the wrong request. It must be the `POST /all-bids-data` request, not page HTML. |
| Mixed-content / CORS error in browser | Modern browsers (Chrome, Firefox, Safari) allow `http://127.0.0.1` from HTTPS pages. If yours blocks it, open the UI locally instead: `python3 -m http.server` from the repo root, then visit `http://localhost:8000`. |

## Privacy

- Your GeM cookies and CSRF token only exist in the local proxy's memory.
- Nothing is written to disk; nothing is sent anywhere except to `bidplus.gem.gov.in`.
- Killing the proxy (Ctrl+C) wipes the tokens.

## Files

| File | Purpose |
|---|---|
| `index.html` | The UI — hosted on GitHub Pages |
| `gem_proxy.py` | Local Python proxy (stdlib only, no `pip install` needed) |
| `CLAUDE.md` | Internal notes for the AI assistant maintaining this repo |

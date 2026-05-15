# BIGMAC E2B Templates Reference

## Available Templates

### Code Interpreter — `bigmac-code-v3-3-1`

**E2B Template ID:** `bigmac-code-v3-3-1` (built 2026-03-28)
**Use for:** Running Python, installing packages, executing shell commands, Playwright browser automation, data analysis, API testing.

✅ **Playwright + Chromium included.** Full browser automation support (feature parity with desktop template).

Pre-installed:

- Python 3, pip, Node.js 22, pnpm
- **Playwright + Chromium browser binaries** (ready to use)
- ffmpeg, imagemagick, tesseract-ocr
- sqlite3, redis-tools, postgresql-client
- Claude Code CLI
- Clawdbot personal AI assistant (optional)

Pool: 2 warm sandboxes managed by CF Worker `e2b-pool-lb`.

**Legacy:** `bigmac-code-v2-9-3` is deprecated (no browser binaries). New pool uses v3-3-1.

### Desktop (VNC) — `bigmac-desktop-v3-3-3`

**E2B Template ID:** `5otn3nktl3v7bp8hza0x`
**Use for:** Visual browser automation, full desktop UI testing, VNC-accessible workflows, tasks needing a real Chrome window, Google-authenticated browsing.

Pre-installed (all of the above plus):

- XFCE desktop environment
- VNC server (noVNC on port 8080)
- Google Chrome for Testing (port 9222 CDP)
- Playwright + Chromium (browser binaries fully installed)
- **Google auth cookies pre-baked** (16 session cookies, ~363 days from 2026-03-28)
  - Covers: `.google.com`, `accounts.google.com`
  - Injected on first boot via `inject-google-cookies.py`
  - Marker: `~/.google-cookies-injected` (skips injection on subsequent boots)
- PyAutoGUI, python-xlib (desktop-control automation)
- DISPLAY=:99 set automatically (xvfb)

Pool: 3 warm sandboxes managed by CF Worker `e2b-pool-lb`.

**VNC URL pattern:** `https://8080-{sandbox_id}.e2b.app/vnc.html?autoconnect=true&resize=scale`

## Pool Architecture

**Single pool manager:** Cloudflare Worker `e2b-pool-lb` at `e2b-pool-lb.sakima-api.workers.dev`

| Pool           | Template              | Size        | Rotation     |
| -------------- | --------------------- | ----------- | ------------ |
| `desktop`      | bigmac-desktop-v3-3-3 | 3 sandboxes | 6h staggered |
| `code`         | bigmac-code-v3-3-1    | 2 sandboxes | 8h staggered |
| `bob_personal` | bigmac-code-v3-3-1    | 1 sandbox   | No rotation  |

State: D1 database. Cron: every 10 min (extend TTL, rotate overdue).

**API endpoints:**

- `GET /health` — pool counts
- `GET /pool/desktop` — desktop sandbox list with VNC URLs
- `GET /pool/code` — code sandbox list
- `GET /pool/status` — full D1 state
- `POST /pool/sync` — force immediate rotation cycle

**Warm pool cache (local):** `~/.openclaw/e2b-desktop-pool.json`

⚠️ **GCP Cloud Run `e2b-sandbox-manager` is LEGACY** — min-instances=0, pending deletion. Do not use.

## Notes

- **Playwright available in both templates** — code interpreter and desktop both support full browser automation.
- **Cookie expiry:** Desktop cookies extracted 2026-03-28. When agents start hitting Google login walls, re-extract and bake v3-3-2.
- **No GitHub cookies:** Ben's Chrome didn't have GitHub session cookies. GitHub auth must be done manually in the sandbox.
- **GOOGLE_API_KEY conflict:** Do NOT set `GOOGLE_API_KEY` in sandbox env — it overrides custom Gemini key priority.
- **Cookie injection timing:** Allow ~10s after desktop sandbox start for cookies to be ready.

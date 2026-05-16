# BIGMAC E2B Template Capability Matrix

## Quick Decision: Which Sandbox Type?

| Need                              | Use                   |
| --------------------------------- | --------------------- |
| Playwright / browser automation   | **desktop**           |
| Web scraping with Chrome/Chromium | **desktop**           |
| VNC / visual desktop              | **desktop**           |
| Google auth (pre-baked cookies)   | **desktop** (v3-3-1+) |
| Pure Python execution             | **code**              |
| Data analysis / pandas / numpy    | **code**              |
| Fast spin-up (no GUI needed)      | **code**              |
| Installing random pip packages    | either                |

## Templates

### bigmac-desktop-v3-3-4 (current default)

- **Type:** Desktop (XFCE + VNC)
- **E2B ID:** `5otn3nktl3v7bp8hza0x`
- **Pool:** 2–3 warm sandboxes always ready in `~/.openclaw/e2b-desktop-pool.json`

**Pre-installed:**

- `google-chrome-for-testing` (system Chrome, headless capable)
- Playwright + Chromium (run `from playwright.sync_api import sync_playwright`)
- All Playwright system deps (70+ libs: libnspr4, libgbm1, etc.)
- PyAutoGUI + python-xlib (desktop automation)
- DISPLAY=:99 (xvfb virtual display already running)
- **Google auth cookies** — 16 cookies injected on first boot via `inject-google-cookies.py`
  - Covers: `.google.com` session cookies (APISID, HSID, SID, SSID, etc.)
  - Valid through ~March 2027 (rebake if Google sessions expire)
  - Marker: `~/.google-cookies-injected` (won't re-inject if present)

**VNC access:**

```
https://8080-<sandbox_id>.e2b.app/vnc.html?autoconnect=true&resize=scale
```

**Running Playwright (correct args for E2B headless):**

```python
browser = await p.chromium.launch(
    headless=True,
    args=["--no-sandbox", "--disable-setuid-sandbox",
          "--disable-dev-shm-usage", "--disable-gpu"]
)
```

---

### bigmac-code-v2-9-3 (code interpreter)

- **Type:** Code Interpreter (no desktop/GUI)
- **Pool:** 5 warm sandboxes always ready

**Pre-installed:**

- Python 3.x + standard data science libs (pandas, numpy, requests, etc.)
- Node.js v22
- No Playwright — **do not attempt browser automation here**
- No Chrome / no display

**To install Playwright if truly needed (slow, ~2 min):**

```bash
pip install playwright && playwright install chromium --with-deps
```

Prefer using a desktop sandbox instead.

---

## Pool Locations

### Desktop pool (fast, pre-warmed):

```python
import json
from pathlib import Path
pool = json.loads(Path("~/.openclaw/e2b-desktop-pool.json").expanduser().read_text())
sandbox_id = pool["sandboxes"][0]["sandbox_id"]
vnc_url = pool["sandboxes"][0]["vnc_url"]
```

### Code pool (managed by GCP Cloud Run):

Available via `sbx ls` — look for `managed_by:e2b-unified-pool pool_type:code_interpreter`.

---

## Common Gotchas

1. **Wrong sandbox type for Playwright** — always use desktop, not code interpreter
2. **Playwright launch args** — must include `--no-sandbox --disable-setuid-sandbox` in E2B
3. **DISPLAY env var** — set `DISPLAY=:99` or `DISPLAY=:0` when running GUI tools
4. **Cookie injection timing** — happens on first boot; wait 5s after sandbox creation before testing Google auth
5. **Pool sandboxes are shared** — don't leave long-running processes; use `--timeout` appropriately
6. **sbx CLI** — `sbx new bigmac-desktop-v3-3-4` spins a fresh one if pool is empty

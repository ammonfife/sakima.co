---
name: e2b-bigmac
description: Use BIGMAC E2B cloud sandboxes for code execution, browser automation, Playwright testing, and web scraping. Use when you need to run code in isolation, test a web page with Playwright, do browser automation, scrape with Chrome, or need a full desktop environment. Covers both desktop sandboxes (bigmac-desktop-v3-3-3 — has Playwright/Chrome/VNC/Google auth cookies) and code interpreter sandboxes (bigmac-code-v2-9-3 — fast, no browser). Do NOT attempt Playwright or Chrome in a code interpreter sandbox.
---

# E2B BIGMAC Sandboxes

## Sandbox Type Decision

**Desktop** (`bigmac-desktop-v3-3-3`): Playwright, Chrome, web scraping, VNC, Google auth
**Code** (`bigmac-code-v2-9-3`): Pure Python/data work, fast spin-up, no browser needed

See [references/templates.md](references/templates.md) for full capability matrix and gotchas.

## Script Location

All scripts live in `scripts/` inside the skill dir. Root-level shims (`acquire.py`, `run_code.py`, `playwright_test.py`) delegate to them. Use either form — both work:

```bash
# From any directory (absolute path):
python3 ~/.claude/skills/e2b-bigmac/acquire.py --type desktop

# From within the skill dir:
cd ~/.claude/skills/e2b-bigmac
python3 acquire.py --type desktop
```

## Acquire a Sandbox

### From pool (fastest — pre-warmed, use first):

```bash
python3 ~/.claude/skills/e2b-bigmac/acquire.py --type desktop   # desktop with Playwright/Chrome
python3 ~/.claude/skills/e2b-bigmac/acquire.py --type code      # code interpreter
```

Outputs JSON: `{"sandbox_id": "...", "type": "...", "vnc_url": "...", "fresh": false}`

### Direct pool read (Python):

```python
import json
from pathlib import Path
pool = json.loads(Path("~/.openclaw/e2b-desktop-pool.json").expanduser().read_text())
sandbox_id = pool["sandboxes"][0]["sandbox_id"]
```

### Force-create fresh:

```bash
python3 ~/.claude/skills/e2b-bigmac/acquire.py --type desktop --fresh
# or via sbx CLI:
sbx new bigmac-desktop-v3-3-3
```

## Run Code in a Sandbox

```bash
# Python code in code interpreter
python3 ~/.claude/skills/e2b-bigmac/run_code.py --id <sandbox_id> --type code --code "import pandas; print(pandas.__version__)"

# Shell command in any sandbox
python3 ~/.claude/skills/e2b-bigmac/run_code.py --id <sandbox_id> --type desktop --shell "ls /home/user"

# Upload and run a script file
python3 ~/.claude/skills/e2b-bigmac/run_code.py --id <sandbox_id> --type code --file my_script.py
```

## Playwright / Browser Automation (desktop only)

```bash
# Test a URL
python3 ~/.claude/skills/e2b-bigmac/playwright_test.py --id <sandbox_id> --url https://example.com

# With screenshot
python3 ~/.claude/skills/e2b-bigmac/playwright_test.py --id <sandbox_id> --url https://lkup.info --screenshot

# Upload custom Playwright script
python3 ~/.claude/skills/e2b-bigmac/playwright_test.py --id <sandbox_id> --script my_playwright.py
```

**Always use these Chromium launch args in E2B:**

```python
args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
```

**Set DISPLAY when running GUI tools:** `DISPLAY=:99`

## Google Auth (desktop v3-3-1+)

16 Google session cookies pre-baked. Injected on first boot automatically.

- Works for: Google Drive, Sheets, Gmail, Cloud Console, Ads, etc.
- Marker file `~/.google-cookies-injected` — injection won't repeat
- Wait 5s after sandbox creation before testing Google auth

```python
# Verify cookies are injected
sbx.commands.run("cat ~/.google-cookies-injected")
```

## VNC / Visual Access

```python
vnc_url = f"https://8080-{sandbox_id}.e2b.app/vnc.html?autoconnect=true&resize=scale"
# Open in browser to see desktop
```

## Test Chrome Extension in E2B

See [test-with-e2b.md](test-with-e2b.md) for the full pattern. Quick summary:

```python
from e2b_desktop import Sandbox
from pathlib import Path

sbx = Sandbox.connect(sandbox_id, api_key=api_key)

# Upload extension files directly (no base64 workaround)
ext_dir = Path("/local/path/to/ext")
sbx.commands.run("mkdir -p /home/user/ext")
for f in ext_dir.rglob("*"):
    if f.is_file():
        sbx.files.write(f"/home/user/ext/{f.relative_to(ext_dir)}", f.read_bytes())

# Launch Chrome with extension
sbx.commands.run(
    "DISPLAY=:99 google-chrome --no-sandbox --no-first-run "
    "--no-default-browser-check --disable-extensions-except=/home/user/ext "
    "--load-extension=/home/user/ext 'https://testurl.com' &",
    timeout=10
)

import time; time.sleep(4)
screenshot = sbx.screenshot()
Path("ext-test.png").write_bytes(screenshot)
```

**Important:** Bump `manifest.json` version before every test run — Chrome caches by version.

## E2B Pool State

- Pool JSON: `~/.openclaw/e2b-desktop-pool.json` (3 sandbox slots when healthy)
- Pool refresh LaunchAgent: `com.ammonfife.e2b-monitor.plist` — currently DISABLED
- To manually refresh: `python3 ~/bigmac-state/scripts/e2b-pool-sync.py`
- Pool source (per global policy): `e2b-pool-lb.sakima-api.workers.dev` — NOT GCP Cloud Run

## E2B API Key

Located at: `bigmac-secrets get e2b_api_key`
All scripts auto-fetch from vault if `E2B_API_KEY` env var not set.

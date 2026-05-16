---
name: e2b-bigmac
description: Use BIGMAC E2B cloud sandboxes for code execution, browser automation, Playwright testing, and web scraping. Use when you need to run code in isolation, test a web page with Playwright, do browser automation, scrape with Chrome, or need a full desktop environment. Covers both desktop sandboxes (bigmac-desktop-v3-3-4 — has Playwright/Chrome/VNC/Google auth cookies) and code interpreter sandboxes (bigmac-code-v2-9-3 — fast, no browser). Do NOT attempt Playwright or Chrome in a code interpreter sandbox.
---

# E2B BIGMAC Sandboxes

## Sandbox Type Decision

**Desktop** (`bigmac-desktop-v3-3-4`): Playwright, Chrome, web scraping, VNC, Google auth
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
sbx new bigmac-desktop-v3-3-4
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

## ⛔ DO NOT INSTALL — Everything Is Pre-Installed

Inside `bigmac-desktop-v3-3-4`, **stop** if you find yourself typing any of these:

```bash
# ❌ Never run inside a desktop sandbox:
pip install playwright
playwright install chromium
apt-get install google-chrome
pip install e2b-desktop
```

**What's already there:**

| Tool | Path / import |
|---|---|
| `google-chrome-for-testing` | `/usr/bin/google-chrome-for-testing` |
| Playwright + Chromium | `from playwright.sync_api import sync_playwright` |
| All system deps (70+ libs) | already installed |
| `xdotool`, `wmctrl` | `/usr/bin/xdotool`, `/usr/bin/wmctrl` |
| ImageMagick | `/usr/bin/convert` |
| PyAutoGUI | `import pyautogui` |

**`sbx` CLI — LOCAL MACHINE ONLY** (runs on your Mac, not inside the sandbox):

```bash
# ✅ Run on your local Mac:
sbx ls                        # list running sandboxes
sbx new bigmac-desktop-v3-3-4 # force-create fresh (when pool empty)
sbx kill <id>                 # kill a sandbox

# ❌ Do NOT run sbx inside the sandbox — it talks to the E2B API from outside
```

**In-sandbox `/home/user/bin/` scripts** (call these from inside the sandbox):

```bash
python3 /home/user/bin/refresh-cookies             # pull fresh cookies from Turso → Chrome DB
python3 /home/user/bin/refresh-cookies --list      # show all browser_auth:* keys in Turso
python3 /home/user/bin/refresh-cookies --domain google.com
```

**Chrome dialog suppression** — the profile is pre-seeded at boot. No dialogs appear because:
- `Local State` has `check_default_browser: false` + far-future `default_browser_infobar_last_shown`
- `Default/Preferences` has `distribution.skip_first_run_ui: true` + `suppress_first_run_bubble: true`
- Profile is named `sakima.lc@gmail.com` with Google as default search
- `First Run` sentinel file exists (Chrome skips welcome page when this is present)
- Launch flags add a belt-and-suspenders layer: `--no-first-run --no-default-browser-check --disable-sync`

If you do launch Chrome manually (not via CDP), use:
```bash
DISPLAY=:99 google-chrome-for-testing \
  --no-first-run --no-default-browser-check --disable-sync \
  --remote-debugging-port=9222 &
```

## Getting Bearings Fast — Once Inside a Desktop

**CRITICAL: Don't `p.chromium.launch()`. Chrome is already running on port 9222 in the desktop sandbox. Use CDP — no launch overhead.**

**Don't pip install anything — Playwright, Selenium, ChromeDriver, xdotool, wmctrl are all pre-installed.**

### Connect via CDP (fastest path)

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
```

### What's on screen — accessibility tree + coords

```python
import json
# Full semantic tree in ~5ms
print(json.dumps(page.accessibility.snapshot(), indent=2))

# All visible clickables with pixel coords
elements = page.evaluate("""
    [...document.querySelectorAll('button,[role=button],a,input,select')]
    .filter(el => el.getBoundingClientRect().width > 0)
    .map(el => ({ text: el.innerText?.trim().slice(0, 40), rect: el.getBoundingClientRect() }))
""")
for el in elements:
    r = el['rect']
    print(f"{el['text']:40} x={r['x']:.0f} y={r['y']:.0f}")
```

### X11 orientation (non-browser)

```python
sbx.commands.run("DISPLAY=:99 wmctrl -l")                                              # list windows
sbx.commands.run("DISPLAY=:99 xdotool getactivewindow getwindowname getwindowgeometry") # active window
sbx.commands.run("DISPLAY=:99 xdotool getmouselocation")                               # cursor position
```

### Click by text — skip coord math

```python
page.get_by_text("Sign In").click()
page.get_by_role("button", name="Submit").click()
page.get_by_placeholder("Search...").fill("query")
```

### Human-like typing + autocomplete

```python
page.hover(selector); page.wait_for_timeout(100); page.click(selector)
page.type("#input", "text", delay=80)   # 80ms/keystroke
# Two-Enter for autocomplete (Whatnot, etc.):
page.type(".search", "query"); page.wait_for_timeout(600)
page.keyboard.press("ArrowDown"); page.keyboard.press("Enter"); page.keyboard.press("Enter")
```

### Wait correctly

```python
page.wait_for_load_state("networkidle")
page.wait_for_selector(".result", timeout=5000)
# NOT: page.wait_for_timeout(3000)  ← never fixed sleep to wait for content
```

## Google Auth (desktop v3-3-1+)

16 Google session cookies pre-baked. Injected on first boot automatically.

- Works for: Google Drive, Sheets, Gmail, Cloud Console, Ads, etc.
- Marker file `~/.google-cookies-injected` — injection won't repeat
- Wait 5s after sandbox creation before testing Google auth

```python
# Verify cookies are injected
sbx.commands.run("cat ~/.google-cookies-injected")
```

## ♻️ Keep the Sandbox Alive — Never Release Between Steps

Releasing and reclaiming between every action wastes 30s per reclaim + burns pool slots.

```
❌ claim → do one thing → release → claim → do one thing → release  (30s tax per action)
✅ claim → do everything → release at end                            (50ms per action)
```

Store the `sandbox_id` at the top of your script and pass it through every function. Release only when the **entire task** is done or the sandbox is broken.

**`sbx` CLI is LOCAL MACHINE ONLY** — runs on your Mac to list/create/kill sandboxes. Do not run it from inside the sandbox.

## VNC / Visual Access

```python
vnc_url = f"https://8080-{sandbox_id}.e2b.app/vnc.html?autoconnect=true&resize=scale"
# Open in browser to see the XFCE desktop + Chrome window
```

**Chrome is VISIBLE (foreground window), NOT headless.** It runs on DISPLAY=:99 which is what VNC shows. You see a real Chrome window in the XFCE desktop — exactly what a user sees.

**VNC "Connect" button:** When you first open the VNC URL, you may see a noVNC splash screen with a "Connect" button. Click it once. After that the desktop is live. The `?autoconnect=true` parameter usually bypasses this but doesn't always work on first visit to a new sandbox.

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

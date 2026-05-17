---
name: bigmac-e2b
description: Spin up and use BIGMAC E2B sandboxes for isolated code execution, Playwright/Selenium browser automation, and full desktop VNC sessions. Use when you need to run Python/shell code in isolation, test with a real browser, execute long-running tasks, get a VNC desktop for visual automation, test scan pages, automate web workflows, or run anything in a clean Linux environment. Two types - (1) code interpreter — fast, headless Playwright/Selenium; (2) desktop — full Chrome + VNC, pre-authenticated with Google cookies. Pool managed by Cloudflare Worker (e2b-pool-lb).
---

# BIGMAC E2B Skill

Two sandbox types. Pick the right one, grab from pool, execute, done.

## ⛔ DO NOT INSTALL — Everything Is Pre-Installed

If you find yourself running any of these, **stop and use the pre-installed versions below instead:**

```
# ❌ NEVER run these inside a desktop sandbox:
pip install playwright
pip install e2b-desktop
playwright install chromium
apt-get install google-chrome
npm install puppeteer
```

**What's already in `bigmac-desktop-v3-3-4`:**

| Tool | Pre-installed path |
|---|---|
| `google-chrome` | `/opt/google/chrome/google-chrome` (NOT `google-chrome-for-testing` — that binary is NOT in PATH) |
| `chromium-browser` | `/usr/bin/chromium-browser` |
| Playwright + Chromium | `python3 -c "from playwright.sync_api import sync_playwright"` |
| All Playwright system deps | 70+ libs (libnspr4, libgbm1, libgbm-dev, etc.) |
| `xdotool` | `/usr/bin/xdotool` |
| `wmctrl` | `/usr/bin/wmctrl` |
| `xrandr`, `xdpyinfo` | `/usr/bin/xrandr`, `/usr/bin/xdpyinfo` |
| `ImageMagick` (import/convert) | `/usr/bin/convert` |
| `PyAutoGUI`, `python-xlib` | `import pyautogui` |

**Bins available inside the sandbox (at `/home/user/bin/`):**

```bash
# Refresh Chrome cookies from Turso (auth baked in — TURSO_AUTH_TOKEN in template env)
python3 /home/user/bin/refresh-cookies             # all domains
python3 /home/user/bin/refresh-cookies --domain google.com
python3 /home/user/bin/refresh-cookies --list      # show what's in Turso

# Full demo: claim → wait → open Chrome → search → click → screenshot + DOM
python3 ~/bin/e2b-desktop-example.py
python3 ~/bin/e2b-desktop-example.py --url https://lkup.info --query "scan"
```

**Local machine bins (run these to control/drive a sandbox from your laptop):**

```bash
~/bin/e2b-desktop-example.py    # complete working demo — claim, browse, click, screenshot
~/bin/e2b-refresh-cookies       # push fresh cookies from Turso into a running sandbox
```

## Choosing a Sandbox Type

| Need                             | Type             | Script           |
| -------------------------------- | ---------------- | ---------------- |
| Run Python / shell commands      | Code interpreter | `sbx_run.py`     |
| Data analysis, API calls, HTTP   | Code interpreter | `sbx_run.py`     |
| Playwright automation (headless) | Code interpreter | `sbx_run.py`     |
| Selenium automation (headless)   | Code interpreter | `sbx_run.py`     |
| Full Chrome window + VNC         | Desktop          | `sbx_desktop.py` |
| Google-authenticated browsing    | Desktop          | `sbx_desktop.py` |
| Visual UI testing                | Desktop          | `sbx_desktop.py` |

✅ **Both templates (`v3-3-1`) have FULL browser support:**

- Playwright + Chromium (ready to go)
- Selenium + ChromeDriver + webdriver-manager + undetected-chromedriver
- All browser binaries pre-installed

**Use code interpreter for most browser tasks** — faster, cheaper. Use desktop when you need a visible window, Google auth, or VNC access.

## Code Interpreter — Quick Start

```bash
# Run Python code
python3 scripts/sbx_run.py --code "import requests; print(requests.get('https://example.com').status_code)"

# Run shell command
python3 scripts/sbx_run.py --shell "curl -s https://api.example.com/data | python3 -m json.tool"

# Run a local script file
python3 scripts/sbx_run.py --file /path/to/script.py

# Keep sandbox alive (reuse for multiple calls)
python3 scripts/sbx_run.py --code "print('first')" --keep
# Output includes sandbox_id → reuse with --sandbox-id <id>
python3 scripts/sbx_run.py --code "print('second')" --sandbox-id <id>

# Quick Playwright test
python3 scripts/sbx_run.py --playwright "https://example.com" --screenshot /tmp/screenshot.png

# Quick Selenium test
python3 scripts/sbx_run.py --selenium "https://example.com" --screenshot /tmp/screenshot.png
```

## Desktop Sandbox — Quick Start

⚠️ **VNC startup latency:** After getting a sandbox, the VNC URL may take **up to 30 seconds** to be viewable. Use `--poll` to wait, or poll manually. Refresh may be required. Sometimes clicking **"Connect"** button is needed.

```bash
# Get warm sandbox from pool (fastest) with polling
python3 scripts/sbx_desktop.py --poll

# Force-create fresh sandbox
python3 scripts/sbx_desktop.py --new

# Run a shell command
python3 scripts/sbx_desktop.py --shell "echo hello" --sandbox-id <id>

# Upload a file to sandbox
python3 scripts/sbx_desktop.py --upload /local/file.py /home/user/file.py --sandbox-id <id>

# Download a file from sandbox
python3 scripts/sbx_desktop.py --download /home/user/output.json /local/output.json --sandbox-id <id>

# Take desktop screenshot
python3 scripts/sbx_desktop.py --screenshot /local/screenshot.png --sandbox-id <id>

# Run Playwright automation
python3 scripts/sbx_desktop.py --playwright "https://example.com" --sandbox-id <id>

# Click an element
python3 scripts/sbx_desktop.py --click "button.submit" --sandbox-id <id>

# Type into a field
python3 scripts/sbx_desktop.py --type "#email" "user@example.com" --sandbox-id <id>

# Kill when done
python3 scripts/sbx_desktop.py --kill <sandbox_id>
```

Output JSON includes `sandbox_id` and `vnc_url`.

## Browser Automation — Bulletproof Patterns

### Playwright (Recommended)

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)  # or headless=False in desktop
    page = browser.new_page()
    page.goto("https://example.com", wait_until="networkidle")

    # Wait + click (with fallback)
    try:
        page.wait_for_selector("button.submit", timeout=5000)
        page.click("button.submit")
    except Exception:
        page.locator("button.submit").first.click(force=True)

    # Type with clear
    page.locator("#email").clear()
    page.locator("#email").fill("user@example.com")

    # Screenshot
    page.screenshot(path="/home/user/screenshot.png")

    browser.close()
```

### Selenium (Alternative)

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    driver.get("https://example.com")
    print("Title:", driver.title)
    driver.save_screenshot("/home/user/screenshot.png")
finally:
    driver.quit()
```

### Undetected ChromeDriver (Anti-Bot)

```python
import undetected_chromedriver as uc

driver = uc.Chrome(headless=True)
driver.get("https://protected-site.com")
# Works on sites with bot detection
driver.quit()
```

## File Operations

```bash
# Upload local → sandbox
python3 scripts/sbx_desktop.py --upload /local/script.py /home/user/script.py --sandbox-id <id>

# Download sandbox → local
python3 scripts/sbx_desktop.py --download /home/user/output.json /local/output.json --sandbox-id <id>

# Read file contents directly
python3 scripts/sbx_desktop.py --shell "cat /home/user/data.txt" --sandbox-id <id>
```

## Screenshot & Visual Verification

```bash
# Desktop screenshot (entire screen)
python3 scripts/sbx_desktop.py --screenshot /tmp/desktop.png --sandbox-id <id>

# Browser page screenshot (via Playwright in code interpreter)
python3 scripts/sbx_run.py --playwright "https://example.com" --screenshot /tmp/page.png
```

## Chrome State on a Fresh Desktop Sandbox

**Chrome IS visible (foreground window in XFCE), NOT headless.** It appears as a real Chrome window inside the VNC desktop — exactly what a user sees. Auto-launched at boot by `start-vnc-desktop.sh`.

**CDP on port 9222 is ready as soon as the sandbox boots.** Connect via CDP immediately — no launch step needed from your script.

**Display is `:0`, not `:99`.** E2B base template starts Xvfb on `:0`. All DISPLAY-dependent commands must use `DISPLAY=:0`.

**VNC "Connect" button:** On first visit to a new sandbox's VNC URL, you may see a noVNC splash with a "Connect" button. Click it once. `?autoconnect=true` usually bypasses it but not always on a brand-new sandbox.

```python
vnc_url = f"https://8080-{sandbox_id}.e2b.app/vnc.html?autoconnect=true&resize=scale"
# Open in browser — click "Connect" if you see a splash screen
```

**If Chrome crashed or was closed**, re-launch it visible:
```python
sbx.commands.run(
    # DISPLAY=:0 (not :99). Binary is /opt/google/chrome/google-chrome (not google-chrome-for-testing)
    "DISPLAY=:0 /opt/google/chrome/google-chrome --no-first-run --no-default-browser-check "
    "--disable-sync --no-sandbox --remote-debugging-port=9222 about:blank &",
    timeout=5
)
time.sleep(6)
```

## Accessing Sandbox Ports from Outside (E2B URL Pattern)

Every sandbox port is exposed via E2B's URL pattern: `{port}-{sandbox_id}.e2b.app`.

```python
# Get the public URL for any port
cdp_host = sbx.get_host(9222)   # → "9222-<sandbox_id>.e2b.app"
vnc_host = sbx.get_host(8080)   # → "8080-<sandbox_id>.e2b.app"

# HTTP services (REST APIs, noVNC) work fine via the E2B tunnel
import urllib.request
with urllib.request.urlopen(f"https://{vnc_host}/vnc.html") as r:
    print(r.status)  # 200

# ⚠️ CDP WebSocket does NOT reliably work over the E2B HTTP tunnel
# Playwright connect_over_cdp("http://9222-<id>.e2b.app") → HTTP 500 or socket hang up
# CORRECT PATTERN for Playwright: upload script → run inside sandbox → download results
```

**Port access pattern (works for HTTP services):**
- noVNC: `https://8080-{sandbox_id}.e2b.app/vnc.html?autoconnect=true`
- Any REST API you start inside: `https://{port}-{sandbox_id}.e2b.app`

**Port access pattern (does NOT work for CDP WebSocket):**
- Chrome CDP: E2B HTTP proxy returns 500 for WebSocket upgrades
- Use the script-upload-and-execute pattern instead (see Human-at-Screen section below)

## Human at the Wheel — Full Desktop Control (SEE → ACT → VERIFY)

This is the primary pattern for "I am an agent operating a desktop like a human." Two layers:

- **Desktop layer** (any app, any window): `xdotool` for mouse/keyboard + `scrot` for screenshots
- **Browser layer** (Chrome specifically): upload a Playwright script → execute inside sandbox → download results

**⚠️ Pool claim/release: use `curl`, not Python `urllib` or `requests`.** Cloudflare bot-detection blocks Python's default User-Agent with HTTP 403. `curl` works. Always:
```python
import subprocess, json
meta = json.loads(subprocess.run(
    ["curl", "-sf", "-X", "POST", f"{POOL_LB}/pool/claim/desktop"],
    capture_output=True, text=True, timeout=15
).stdout)
SBX_ID = meta["sandbox_id"]
```

**⚠️ DISPLAY is `:0`, not `:99`.** Template uses DISPLAY=:0. All commands require `DISPLAY=:0`.

**⚠️ Screenshots: never let base64 hit the agent conversation — each image is ~20K tokens as base64 text.** The base64 must be captured as a Python variable and decoded silently, never printed/echoed. Agent then uses the `Read` tool on the saved `.png` file — Claude sees it via vision at ~0 token cost. See `see()` primitive below.

After template v3.3.5 rebuild, `sbx.screenshot()` returns bytes directly — no base64 needed.

**⚠️ `sbx.files.read()` returns a string, not bytes.** Use base64 for binary files.

**⚠️ `CommandExitException` is raised on ANY non-zero exit.** Wrap every `sbx.commands.run()` call in try/except.

### The canonical primitives (copy these verbatim)

```python
import base64, time
from e2b_desktop import Sandbox
from e2b.sandbox.commands.command_handle import CommandExitException

def run(sbx, cmd, timeout=15):
    """Run command inside sandbox, never raise on non-zero exit."""
    try:
        r = sbx.commands.run(cmd, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), 0
    except CommandExitException as e:
        return "", str(e)[:200], 1

def see(sbx, label, out_dir):
    """SEE: Take desktop screenshot → download as PNG bytes."""
    run(sbx, f"DISPLAY=:0 scrot /tmp/{label}.png")
    b64, _, rc = run(sbx, f"base64 /tmp/{label}.png", timeout=15)
    if b64 and rc == 0:
        png = base64.b64decode(b64)
        (out_dir / f"{label}.png").write_bytes(png)
        return png
    return None

def click(sbx, x, y, button=1):
    """ACT: Move mouse to (x,y) and click."""
    run(sbx, f"DISPLAY=:0 xdotool mousemove {x} {y} click {button}")

def move(sbx, x, y):
    run(sbx, f"DISPLAY=:0 xdotool mousemove {x} {y}")

def type_text(sbx, text, delay=80):
    """ACT: Type text with human-like keystroke delay."""
    escaped = text.replace("'", "'\\''")
    run(sbx, f"DISPLAY=:0 xdotool type --delay {delay} '{escaped}'")

def key(sbx, k):
    """ACT: Press a keyboard key (e.g. 'Return', 'ctrl+a', 'alt+F2')."""
    run(sbx, f"DISPLAY=:0 xdotool key {k}")

def windows(sbx):
    """ORIENT: List all open windows with IDs."""
    out, _, _ = run(sbx, "DISPLAY=:0 wmctrl -l")
    return out

def where(sbx):
    """ORIENT: Get current mouse cursor position."""
    out, _, _ = run(sbx, "DISPLAY=:0 xdotool getmouselocation")
    return out

def run_playwright_inside(sbx, script_code, timeout=60):
    """BROWSER: Run a Playwright script inside the sandbox, return results dict."""
    sbx.files.write("/tmp/_pw_task.py", script_code)
    out, err, rc = run(sbx, "python3 /tmp/_pw_task.py", timeout=timeout)
    return {"stdout": out, "stderr": err, "rc": rc}

def get_page_screenshot(sbx, url, out_path):
    """BROWSER: Navigate to URL, return Playwright screenshot bytes."""
    script = f"""
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("{url}", wait_until="domcontentloaded", timeout=25000)
    page.wait_for_timeout(1500)
    page.screenshot(path="/tmp/_pw_shot.png")
    browser.close()
"""
    run_playwright_inside(sbx, script)
    b64, _, _ = run(sbx, "base64 /tmp/_pw_shot.png", timeout=10)
    if b64:
        png = base64.b64decode(b64)
        out_path.write_bytes(png)
        return png
```

### The SEE → ACT → VERIFY loop

```python
from pathlib import Path
OUT = Path.home() / "clawd/data/e2b-work"
OUT.mkdir(parents=True, exist_ok=True)

# 1. SEE what's on screen
see(sbx, "before_action", OUT)

# 2. ACT — desktop level (any app)
click(sbx, 640, 45)           # click address bar
key(sbx, "ctrl+a")            # select all
type_text(sbx, "https://lkup.info")
key(sbx, "Return")
time.sleep(2)

# 3. VERIFY
see(sbx, "after_nav", OUT)    # visual proof

# 4. BROWSER ACT — for Chrome specifically
get_page_screenshot(sbx, "https://lkup.info/inventory", OUT / "inventory.png")
```

### Orient on a web page: accessibility tree + coord dump

This runs as a Playwright script inside the sandbox:

```python
orient_script = """
from playwright.sync_api import sync_playwright
import json
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # Semantic tree — every role/name/clickable
    snap = page.accessibility.snapshot()
    print("SNAP:" + json.dumps(snap)[:2000])

    # All clickables with coords
    elems = page.evaluate('''
        [...document.querySelectorAll("button,[role=button],a,input,select")]
        .filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; })
        .slice(0, 15)
        .map(el => ({
            text: (el.innerText || el.value || el.placeholder || "").trim().slice(0, 35),
            tag: el.tagName,
            x: el.getBoundingClientRect().x,
            y: el.getBoundingClientRect().y
        }))
    ''')
    for el in elems:
        print(f"ELEM:{el['tag']}|{el['text']}|x={el['x']:.0f}|y={el['y']:.0f}")
    browser.close()
"""
result = run_playwright_inside(sbx, orient_script)
for line in result["stdout"].split("\\n"):
    print(line)
```

### Orient on X11 desktop (non-browser windows)

```python
# List all open windows
out, _, _ = run(sbx, "DISPLAY=:0 wmctrl -l")

# Active window name + geometry
out, _, _ = run(sbx, "DISPLAY=:0 xdotool getactivewindow getwindowname getwindowgeometry")

# Mouse position
out, _, _ = run(sbx, "DISPLAY=:0 xdotool getmouselocation")

# Find a window by name and click inside it
run(sbx, """
DISPLAY=:0
WID=$(xdotool search --name 'Files' | head -1)
xdotool windowactivate --sync $WID
xdotool mousemove --window $WID 200 150 click 1
""")
```

### Click by text — no coords needed

```python
page.get_by_text("Sign In").click()
page.get_by_role("button", name="Submit").click()
page.get_by_placeholder("Search...").fill("query")
page.get_by_label("Email").fill("user@example.com")
```

### Human-like interaction (avoid bot detection)

```python
page.hover(selector)            # hover first — many sites require it
page.wait_for_timeout(100)      # brief human pause
page.click(selector)

page.type("#input", "text", delay=80)  # 80ms per keystroke feels human

# Autocomplete / dropdowns: type → wait → arrow → enter → enter
page.type(".search", "1881-S Morgan")
page.wait_for_timeout(600)              # wait for dropdown
page.keyboard.press("ArrowDown")
page.keyboard.press("Enter")           # select from dropdown
page.keyboard.press("Enter")           # confirm/send (Whatnot needs two Enters)
```

### Wait correctly — never fixed sleep

```python
page.wait_for_load_state("networkidle")           # no pending XHR
page.wait_for_selector(".result", timeout=5000)   # DOM element appears
page.wait_for_function("() => document.querySelectorAll('.item').length > 0")
# For SPAs only: page.wait_for_timeout(200) is OK after navigation
```

### See-act-verify loop (rapid feedback)

```python
from pathlib import Path

before = page.screenshot()
page.click("#button")
page.wait_for_timeout(300)     # let DOM settle
after = page.screenshot()
Path("~/clawd/data/e2b-proof.png").expanduser().write_bytes(after)
```

## Self-Sufficient Testing Pattern

When testing your own work, don't ask Ben to verify — grab a sandbox and test yourself:

```bash
# 1. Get sandbox, run test
python3 scripts/sbx_run.py --keep --code "
# your test code here
assert result == expected, f'FAIL: {result}'
print('PASS')
"

# 2. If visual verification needed
python3 scripts/sbx_desktop.py --poll  # get desktop
python3 scripts/sbx_desktop.py --screenshot /tmp/result.png --sandbox-id <id>
# Then use image tool to verify
```

## Pool & Templates

See `references/templates.md` for template details and pool architecture.

**Quick reference:**

- Code: `bigmac-code-v3-3-1` (Playwright + Selenium + browsers)
- Desktop: `bigmac-desktop-v3-3-4` (Chrome + VNC + Google cookies)
- Pool API: `https://e2b-pool-lb.sakima-api.workers.dev/health`

## ♻️ KEEP THE SANDBOX ALIVE — Do Not Release Between Actions

**This is the most expensive mistake agents make: releasing and reclaiming a sandbox between every test or action.**

Each cold start = ~30s wait for desktop + Chrome. Reusing the same sandbox = ~50ms per action.

```
❌ WRONG — kills tokens and time:
  claim sandbox → do one thing → release → claim sandbox → do one thing → release

✅ RIGHT — claim once, do everything, release at the end:
  claim sandbox → test A → test B → test C → screenshot → release
```

**Rule: one sandbox per task session.** Keep it alive for the whole flow:

```python
# ✅ Claim once at the top
sandbox_id = pool_claim()
sbx = Sandbox.connect(sandbox_id, api_key=E2B_API_KEY)

# Do ALL your work with the same sandbox
run_test_a(sbx, page)
run_test_b(sbx, page)
take_screenshots(sbx, page)

# Release only when the entire task is done
pool_release(sandbox_id)
```

**Only release early if:**
- The task genuinely finished (not just one step of it)
- The sandbox is corrupted / Chrome crashed
- You've been in it >45 min and need a fresh state

**Store the sandbox_id in a variable at the top of every script. Pass it through the whole flow. Never re-claim mid-task.**

## Important Notes

- **Keep alive:** One sandbox per task. Don't release between steps.
- **VNC latency:** Up to 30s on first boot. Pool sandboxes are pre-warmed — connect via CDP immediately.
- **Cookie injection:** Desktop cookies ready ~10s after boot. `bin/refresh-cookies` pulls latest from Turso.
- **Timeout default:** 300s code, 3600s desktop. Pass `--timeout` to override.
- **`sbx` CLI is LOCAL MACHINE ONLY** — runs on your Mac to manage sandboxes, not inside the sandbox itself.

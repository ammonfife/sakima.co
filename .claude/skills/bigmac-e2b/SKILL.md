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
| `google-chrome-for-testing` | `/usr/bin/google-chrome-for-testing` |
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

**VNC "Connect" button:** On first visit to a new sandbox's VNC URL, you may see a noVNC splash with a "Connect" button. Click it once. `?autoconnect=true` usually bypasses it but not always on a brand-new sandbox.

```python
vnc_url = f"https://8080-{sandbox_id}.e2b.app/vnc.html?autoconnect=true&resize=scale"
# Open in browser — click "Connect" if you see a splash screen
```

**If Chrome crashed or was closed**, re-launch it visible:
```python
sbx.commands.run(
    "DISPLAY=:99 google-chrome-for-testing --no-first-run --no-default-browser-check "
    "--disable-sync --no-sandbox --remote-debugging-port=9222 about:blank &",
    timeout=5
)
time.sleep(4)
```

## Getting Bearings Fast — Once Inside a Desktop

**CRITICAL: Don't launch a new browser. Chrome is already running on port 9222. Connect via CDP — no launch latency.**

**Don't pip install anything. Every browser tool is pre-installed: Playwright, Selenium, ChromeDriver, undetected-chromedriver, xdotool, wmctrl, ImageMagick.**

### Fastest: CDP connect (skip browser launch entirely)

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    # connected in ~50ms — no 5-10s launch overhead
```

### Orient on a web page: accessibility tree + coord dump

```python
import json

# Full semantic tree — every role/name/clickable in ~5ms
snapshot = page.accessibility.snapshot()
print(json.dumps(snapshot, indent=2))

# All visible clickables with pixel coords
elements = page.evaluate("""
    [...document.querySelectorAll('button,[role=button],a,input,select')]
    .filter(el => { const r = el.getBoundingClientRect(); return r.width > 0; })
    .map(el => ({ text: el.innerText?.trim().slice(0, 40), rect: el.getBoundingClientRect() }))
""")
for el in elements:
    r = el['rect']
    print(f"{el['text']:40} x={r['x']:.0f} y={r['y']:.0f}")
```

### Orient on the X11 desktop (non-browser windows)

```python
# What windows are open
result = sbx.commands.run("DISPLAY=:99 wmctrl -l")

# Active window name + geometry
result = sbx.commands.run("DISPLAY=:99 xdotool getactivewindow getwindowname getwindowgeometry")

# Mouse cursor position
result = sbx.commands.run("DISPLAY=:99 xdotool getmouselocation")

# Find window by name → click inside it
sbx.commands.run("""
DISPLAY=:99 WID=$(xdotool search --name 'Files' | head -1)
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

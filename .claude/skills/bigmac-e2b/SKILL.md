---
name: bigmac-e2b
description: Spin up and use BIGMAC E2B sandboxes for isolated code execution, Playwright/Selenium browser automation, and full desktop VNC sessions. Use when you need to run Python/shell code in isolation, test with a real browser, execute long-running tasks, get a VNC desktop for visual automation, test scan pages, automate web workflows, or run anything in a clean Linux environment. Two types - (1) code interpreter — fast, headless Playwright/Selenium; (2) desktop — full Chrome + VNC, pre-authenticated with Google cookies. Pool managed by Cloudflare Worker (e2b-pool-lb).
---

# BIGMAC E2B Skill

Two sandbox types. Pick the right one, grab from pool, execute, done.

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
- Desktop: `bigmac-desktop-v3-3-3` (Chrome + VNC + Google cookies)
- Pool API: `https://e2b-pool-lb.sakima-api.workers.dev/health`

## Important Notes

- **Always clean up:** Kill sandboxes when done (`--kill`). Pool auto-replenishes.
- **VNC latency:** Up to 30s to be viewable. Use `--poll` or poll manually.
- **Cookie injection:** Desktop cookies ready ~10s after boot.
- **Timeout default:** 300s code, 3600s desktop. Pass `--timeout` to override.

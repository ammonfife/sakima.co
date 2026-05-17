# /use-e2b

> **Merge-additive notice (Ben 2026-05-02):** A `/use-e2b` skill predates this file in another agent context (likely `~/clawd/.claude/skills/use-e2b/` or `~/.openclaw/skills/use-e2b/` on Bob's laptop). This file is the lkup.info-repo authoritative version covering the auth-precedence + lkup-specific E2B pattern. **When the cross-repo skills are reconciled, MERGE this content into the pre-existing skill — do not replace.** Bob has a TODO in `docs/SANDBOX_LIMITED_TODOS_2026-05-02.md` to perform that reconciliation from the laptop. This file remains the canonical reference inside this repo.

Foundation skill for spawning, driving, and tearing down E2B desktop / code sandboxes for any task that needs a real browser, full Linux runtime, or interactive shell beyond Claude Code's local environment.

## When to use

- Any browser automation (auth flows, UI test, scrape, screenshot)
- Browser extension load + test (Chrome dev mode, manifest v3)
- Native desktop testing (Electron, Tauri prototypes)
- Long-running workloads that exceed the local sandbox
- Anything that needs a real X server / display

Do NOT use for: simple file edits, lint, unit tests that already run locally, anything `Bash` + `Read` + `Edit` can do directly.

## Pool

The pool lives behind `e2b-pool-lb`:
- `https://e2b-pool-lb.sakima-api.workers.dev`
- `GET /pool/desktop` — list available desktop sandboxes
- `GET /pool/code` — list available code-interpreter sandboxes
- `POST /pool/claim/desktop` — claim a desktop (TTL 30 min)
- `POST /pool/claim/code` — claim a code sandbox
- `POST /pool/release/<sandbox_id>` — release after use
- Hard cap: 60 concurrent sandboxes account-wide

## Auth precedence (Ben 2026-05-02): "Prefer cookies over GUI sign-in, but failsafe to all methods"

Every browser-auth flow must implement this fallback chain:

1. **Cookies first** — pull `browser_auth:<host>:<profile>` from Turso `secrets` table; restore via Playwright `storage_state`. Verify session is alive before proceeding.
2. **Email + password fallback** — if cookies expired/missing, attempt direct login using `.env` credentials (`BEN_EMAIL_PRIMARY` + a password from the candidate set, e.g., `EBAY_PASS`, `WHATNOT_PASS`, etc.).
3. **OAuth (Google/GitHub) fallback** — if password auth fails or service is OAuth-only, drive the OAuth flow with Turso-stored `browser_auth:accounts.google.com:*` and `browser_auth:github.com:*` cookies.
4. **Manual GUI failsafe** — if all of the above fail, surface the live VNC URL and the exact step that needs human intervention. Don't pretend success.

After any successful login: write fresh cookies back to Turso so the next agent's "cookies first" path works.

## Standard driver pattern (Python, Playwright)

```python
import os, json, libsql_client
from playwright.async_api import async_playwright
import requests

POOL_LB = "https://e2b-pool-lb.sakima-api.workers.dev"

# 1. Claim sandbox
# Use curl — Python urllib/requests may get 403 from Cloudflare bot detection
import subprocess, json as _json
_r = subprocess.run(["curl", "-sf", "-X", "POST", f"{POOL_LB}/pool/claim/desktop"],
                    capture_output=True, text=True, timeout=15)
sandbox = _json.loads(_r.stdout)
sb_id = sandbox["sandbox_id"]
vnc = sandbox.get("vnc_url", f"https://8080-{sb_id}.e2b.app/vnc.html?autoconnect=true")

# 2. Pull cookies from Turso (PREFER)
turso = libsql_client.create_client(
    url=os.environ["TURSO_DATABASE_URL"],
    auth_token=os.environ["TURSO_AUTH_TOKEN"],
)
row = turso.execute(
    "SELECT value FROM secrets WHERE key = ?",
    ["browser_auth:lovable.dev"]
).rows[0]
storage_state = json.loads(row["value"])

# 3. Drive browser
async with async_playwright() as p:
    browser = await p.chromium.connect_over_cdp(sandbox["cdp_url"])
    ctx = await browser.new_context(storage_state=storage_state)
    page = await ctx.new_page()
    await page.goto("https://lovable.dev/projects/...")

    # Verify session alive — look for a "logged in" sentinel
    if await page.locator("text=Sign in").is_visible(timeout=5000):
        # Cookies dead — fall through to password auth
        ...
    else:
        # Do the work
        await page.click("button:has-text('Publish')")

# 4. Write fresh cookies back to Turso
fresh_state = await ctx.storage_state()
turso.execute(
    "UPDATE secrets SET value = ?, updated_at = ? WHERE key = ?",
    [json.dumps(fresh_state), int(time.time()), "browser_auth:lovable.dev"]
)

# 5. ALWAYS release the sandbox
subprocess.run(["curl", "-sf", "-X", "POST", f"{POOL_LB}/pool/release/{sb_id}"], timeout=10)
```

## Critical: DISPLAY, Ports, and Playwright Connection

**DISPLAY is `:0`, NOT `:99`.** Every xdotool/scrot/xrandr command needs `DISPLAY=:0`. Until template v3.3.5, inject it at session start so SDK native methods also work:
```python
sbx.commands.run("grep -q 'DISPLAY=:0' /etc/environment 2>/dev/null || echo 'DISPLAY=:0' >> /etc/environment")
```

**Screenshots: never let base64 hit the agent conversation.** A 60KB PNG = ~20K tokens as base64 text. Capture as a Python variable, decode silently, write to disk. Agent then uses `Read` tool on the PNG — Claude vision reads it at ~0 token cost.
```python
# CORRECT — base64 captured as Python variable, never echoed to stdout
sbx.commands.run("DISPLAY=:0 scrot /tmp/shot.png")
b64 = sbx.commands.run("base64 /tmp/shot.png", timeout=15).stdout.strip()
Path("~/clawd/data/shot.png").expanduser().write_bytes(base64.b64decode(b64))
# Then: Read("~/clawd/data/shot.png") — costs ~0 tokens, full vision

# ❌ NEVER — this floods the conversation with 20K+ tokens:
# sbx.commands.run("base64 /tmp/shot.png")  # as a bare Bash tool call
```

After template v3.3.5: `sbx.screenshot()` returns bytes directly — no base64 needed.

**`sbx.files.read()` returns a string, not bytes.** Use base64 for binary files.

**`CommandExitException` is raised on any non-zero exit.** Always wrap:
```python
from e2b.sandbox.commands.command_handle import CommandExitException
try:
    r = sbx.commands.run(cmd, timeout=15)
except CommandExitException:
    pass  # handle gracefully
```

**Port access from outside:** `sbx.get_host(port)` → `{port}-{sandbox_id}.e2b.app`
- HTTP services: work fine via E2B tunnel
- CDP WebSocket (port 9222): **E2B tunnel returns HTTP 500 for WebSocket upgrades** — does NOT work for `p.chromium.connect_over_cdp()` from outside
- **Workaround**: upload Playwright script to sandbox → run inside → download screenshots

## Getting Bearings Fast — Once Inside a Desktop

**Don't launch a new browser. Connect via CDP to Chrome already running on port 9222 INSIDE the sandbox.**
**Don't pip install — Playwright, xdotool, wmctrl are pre-installed in every desktop template.**

### Playwright from INSIDE the sandbox (correct pattern)

Upload a `.py` script to `/tmp/`, execute it inside, download the results:

```python
import base64

script = """
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://example.com", wait_until="domcontentloaded", timeout=25000)
    page.wait_for_timeout(1500)
    print(f"TITLE:{page.title()}")
    page.screenshot(path="/tmp/result.png")
    browser.close()
"""
sbx.files.write("/tmp/pw_task.py", script)
out = sbx.commands.run("python3 /tmp/pw_task.py", timeout=60).stdout
print(out)

# Download screenshot (binary via base64)
b64 = sbx.commands.run("base64 /tmp/result.png", timeout=10).stdout.strip()
png = base64.b64decode(b64)
Path("~/clawd/data/result.png").expanduser().write_bytes(png)
```

### Human-at-the-Wheel: SEE → ACT → VERIFY loop

Full desktop control — operates any app visible in VNC, not just Chrome:

```python
import base64, time
from pathlib import Path
from e2b.sandbox.commands.command_handle import CommandExitException

def run(cmd, timeout=15):
    try:
        r = sbx.commands.run(cmd, timeout=timeout)
        return r.stdout.strip(), 0
    except CommandExitException:
        return "", 1

def see(label):
    """Take full desktop screenshot → return PNG bytes."""
    run(f"DISPLAY=:0 scrot /tmp/{label}.png")
    b64, rc = run(f"base64 /tmp/{label}.png", timeout=15)
    if b64:
        png = base64.b64decode(b64)
        Path(f"~/clawd/data/{label}.png").expanduser().write_bytes(png)
        return png

def click(x, y, button=1):
    run(f"DISPLAY=:0 xdotool mousemove {x} {y} click {button}")

def type_text(text, delay=80):
    escaped = text.replace("'", "'\\''")
    run(f"DISPLAY=:0 xdotool type --delay {delay} '{escaped}'")

def key(k):
    run(f"DISPLAY=:0 xdotool key {k}")

# Example: open a terminal, run a command, screenshot the result
see("before")
key("alt+F2")             # XFCE run dialog
time.sleep(0.5)
type_text("xterm")
key("Return")
time.sleep(2)
see("xterm_open")
```

### Orient immediately — accessibility snapshot + coord dump

Run this as a Playwright script inside the sandbox (not from local Mac):

```python
orient_script = """
from playwright.sync_api import sync_playwright
import json
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    page = browser.contexts[0].pages[0]

    snap = page.accessibility.snapshot()
    for n in (snap.get('children') or [])[:12]:
        if n.get('name'): print(f"  [{n['role']}] {n['name'][:50]}")

    elems = page.evaluate('''
        [...document.querySelectorAll("button,a,input")]
        .filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; })
        .slice(0, 15)
        .map(el => ({
            text: (el.innerText || el.placeholder || "").trim().slice(0, 35),
            tag: el.tagName,
            x: el.getBoundingClientRect().x,
            y: el.getBoundingClientRect().y
        }))
    ''')
    for el in elems:
        print(f"ELEM:{el['tag']}|{el['text']}|x={el['x']:.0f}|y={el['y']:.0f}")
    browser.close()
"""
sbx.files.write("/tmp/orient.py", orient_script)
print(sbx.commands.run("python3 /tmp/orient.py", timeout=20).stdout)
```

### X11 desktop orientation (non-browser apps)

```python
run("DISPLAY=:0 wmctrl -l")                                               # list all windows
run("DISPLAY=:0 xdotool getactivewindow getwindowname getwindowgeometry")  # active window info
run("DISPLAY=:0 xdotool getmouselocation")                                 # cursor coords
```

## Failure-mode handling

| Failure | Diagnosis | Resolution |
|---|---|---|
| Pool returns `503 {"error":"pool at hard cap"}` | All 60 sandboxes claimed | Wait 30 min for TTL reaper, OR release stuck claims via `POST /pool/release/<id>` |
| Cookies fail with `Sign in` redirect | Session expired in Turso | Drop to step 2 (password) or step 3 (OAuth) |
| Password auth returns `INVALID_LOGIN_CREDENTIALS` | Wrong .env key | Try the next candidate; if all fail, surface VNC URL for human |
| Sandbox VNC URL dead | Sandbox killed mid-task | Re-claim from pool (if you still have data, persist via Turso write) |
| `wrangler` / Playwright timeout | Network or service-side issue | Retry with exponential backoff (2s, 4s, 8s); after 4 failures, escalate |

## Claim-and-release discipline

- ALWAYS release on success.
- ALWAYS release on failure (try/finally pattern in driver script).
- If a session crashes without release, the 30-min TTL reaper will recover the slot — but pool capacity suffers in the interim.
- For long-running tasks (>30 min), refresh the claim periodically via `POST /pool/refresh/<id>`.

## Logging + audit

Every sandbox use writes a row to `raw.e2b_run_logs`:
- `sandbox_id`
- `claimed_at`, `released_at`
- `task_description`
- `outcome` (`success` | `auth_fallback` | `failed`)
- `vnc_url_archived` (in case Ben needs to debug)

This is append-only per the `raw.*` rule. Never UPDATE/DELETE.

## Reference: existing E2B-using surfaces

- `cloudflare/e2b-pool-lb-cf/` — the load balancer worker
- `auction_tools/lkup_info_site/cloud_run/scripts/e2b_*` — legacy pool scripts (deprecated)
- `bigmac` repo — primary consumer of E2B for nightly automation
- This skill is the canonical "from a Claude session, use E2B safely" path. Other surfaces predate it.

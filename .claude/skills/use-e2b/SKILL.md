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
sandbox = requests.post(f"{POOL_LB}/pool/claim/desktop").json()
sb_id = sandbox["sandbox_id"]
vnc = sandbox["vnc_url"]

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
requests.post(f"{POOL_LB}/pool/release/{sb_id}")
```

## Getting Bearings Fast — Once Inside a Desktop

**Don't launch a new browser. Connect via CDP to Chrome already running on port 9222.**
**Don't pip install — Playwright, xdotool, wmctrl are pre-installed in every desktop template.**

### CDP connect — no launch latency

```python
async with async_playwright() as p:
    browser = await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
```

### Orient immediately — accessibility snapshot + coord dump

```python
import json
# Full semantic tree of every clickable element — ~5ms
snapshot = await page.accessibility.snapshot()
print(json.dumps(snapshot, indent=2))

# Pixel coords for every visible button/link/input
elements = await page.evaluate("""
    [...document.querySelectorAll('button,[role=button],a,input,select')]
    .filter(el => el.getBoundingClientRect().width > 0)
    .map(el => ({ text: el.innerText?.trim().slice(0, 40), rect: el.getBoundingClientRect() }))
""")
for el in elements:
    r = el['rect']
    print(f"{el['text']:40} x={r['x']:.0f} y={r['y']:.0f}")
```

### Click by text — no pixel math

```python
await page.get_by_text("Sign In").click()
await page.get_by_role("button", name="Publish").click()
await page.get_by_placeholder("Search...").fill("1881-S Morgan")
```

### Human-like interaction

```python
await page.hover(selector); await page.wait_for_timeout(100); await page.click(selector)
await page.type("#input", "text", delay=80)   # 80ms/keystroke
# Two-Enter for autocomplete fields:
await page.type(".chat", "text"); await page.wait_for_timeout(600)
await page.keyboard.press("ArrowDown"); await page.keyboard.press("Enter"); await page.keyboard.press("Enter")
```

### Correct waits (never fixed sleep for content)

```python
await page.wait_for_load_state("networkidle")
await page.wait_for_selector(".result", timeout=5000)
# page.wait_for_timeout(200) only OK as tiny post-navigation gap in SPAs
```

### See-act-verify loop

```python
before = await page.screenshot()
await page.click("#button"); await page.wait_for_timeout(300)
after = await page.screenshot()
Path("~/clawd/data/e2b-proof.png").expanduser().write_bytes(after)
```

### X11 desktop orientation (non-browser apps)

```python
sbx.commands.run("DISPLAY=:99 wmctrl -l")                                               # list all windows
sbx.commands.run("DISPLAY=:99 xdotool getactivewindow getwindowname getwindowgeometry")  # active window info
sbx.commands.run("DISPLAY=:99 xdotool getmouselocation")                                # cursor coords
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

# /browser-test

Run unit tests, integration tests, and interactive debugging for the React web app + browser extensions, using local Vitest where possible and E2B desktop sandboxes (`/use-e2b`) when a real browser or extension runtime is required.

## When to use

- Vitest-only refactor → just run `npm run test` directly, don't invoke this skill.
- React component test that needs real browser rendering, network, or storage → this skill.
- Any test of `extension/` (cert-scraper, price-overlay, ebay-import) → this skill, since the extension is Chrome MV3 and can't run under jsdom.
- Live-debugging a flaky path in production → this skill, with screenshot + console capture.

## Test layers

| Layer | Tool | Where it runs | This skill needed? |
|---|---|---|---|
| Pure logic unit tests (`shared/barcode-parser/*.test.ts`) | Vitest | Local Node | No — `npm run test` |
| React component tests with jsdom (`src/**/*.test.tsx`) | Vitest + jsdom | Local Node | No — `npm run test` |
| Browser-rendering tests (real DOM, real fonts) | Playwright in E2B desktop | E2B sandbox | Yes |
| Extension content-script tests | Playwright + extension load in E2B | E2B sandbox | Yes |
| Extension service-worker / MV3 manifest tests | Chrome dev mode in E2B | E2B sandbox | Yes |
| Visual regression / screenshot diff | Playwright + pixelmatch in E2B | E2B sandbox | Yes |

## Browser test pattern (web app)

```python
# 1. Claim E2B desktop (see /use-e2b)
# 2. Build the React app (Vite) — locally first if possible
#    npm run build  → dist/
# 3. Sync dist/ + a static server into the sandbox
# 4. Run Playwright suite against http://localhost:8080

# Skeleton (driver.py):
import asyncio, requests, json
from playwright.async_api import async_playwright

POOL = "https://e2b-pool-lb.sakima-api.workers.dev"
sandbox = requests.post(f"{POOL}/pool/claim/desktop").json()

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(sandbox["cdp_url"])
        page = await browser.new_page()
        await page.goto("http://localhost:8080/scan")

        # Test: scan flow renders cert + service after barcode submit
        await page.fill("input[name='barcode']", "NGC-1234567-001")
        await page.click("button[type='submit']")
        await page.wait_for_url("**/coin/**", timeout=10_000)

        # Capture for debug
        await page.screenshot(path="/tmp/scan-result.png", full_page=True)
        print("PASS: scan → coin redirect")

asyncio.run(run())
requests.post(f"{POOL}/pool/release/{sandbox['sandbox_id']}")
```

## Extension test pattern

The extension lives in `extension/` (manifest v3, service worker + content scripts).

```python
# 1. Build / package the extension
#    cd extension && npm run build   (if a build step exists; otherwise it's static)
# 2. Claim E2B desktop with Chrome installed
# 3. Launch Chrome with --load-extension=<path>
# 4. Navigate to a target site (whatnot.com, ngccoin.com) and verify content-script behavior

# Driver:
async def run():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir="/tmp/chrome-profile",
            headless=False,
            args=[
                f"--load-extension=/home/user/lkup.info/extension",
                f"--disable-extensions-except=/home/user/lkup.info/extension",
            ],
        )

        # Open Whatnot, verify the price-overlay injects
        page = await ctx.new_page()
        await page.goto("https://www.whatnot.com/live/...")
        # Wait for content script to inject the overlay
        await page.locator(".lkup-price-overlay").wait_for(timeout=15_000)

        # Inspect background service worker logs
        sw = ctx.service_workers[0]
        logs = await sw.evaluate("() => console.history")  # if instrumented
        # Or: open chrome://extensions and capture errors

asyncio.run(run())
```

## Debugging flow

When a test fails, this skill captures (in priority order):

1. **Screenshot at failure** — `await page.screenshot(path=...)`. Persist to Turso `raw.e2b_run_logs.screenshot_url` (link to a Cloudflare R2 upload), so the failure is reviewable later.
2. **Console + network logs** — Playwright's `page.on("console")` + `page.on("response")` listeners. JSONL dump.
3. **Storage state** — `await ctx.storage_state()` — captures cookies + localStorage at failure time.
4. **VNC URL** — surface `https://8080-<sandbox_id>.e2b.app/vnc.html` so a human can drive the live session if needed.
5. **Sandbox preserved on failure** — do NOT release the sandbox immediately on test failure; leave it claimed for 5 minutes so a human can VNC in and inspect. Auto-release after 5 min via a deferred call (or rely on the 30-min TTL reaper).

## Auth handling for tests

Per `/use-e2b` rule: cookies first, password fallback, OAuth fallback, manual VNC failsafe. For tests against authenticated routes:

```python
# Pull test-account cookies from Turso (NOT prod cookies)
storage = json.loads(turso.execute(
    "SELECT value FROM secrets WHERE key = ?",
    ["browser_auth:test:lkup.info"]
).rows[0]["value"])

ctx = await browser.new_context(storage_state=storage)
```

Maintain a separate `browser_auth:test:*` set of credentials in Turso so test runs don't pollute Ben's prod session cookies. If the test account doesn't exist yet, that's an action item for `/use-e2b`'s next iteration.

## Extension-specific gotchas

- **Manifest v3 service workers timeout** after 30 sec idle. Tests that depend on a long-running background task must either keep the SW awake (`chrome.alarms`) or accept the restart.
- **`chrome.storage.local`** is per-profile — make sure tests use a fresh `user_data_dir` to avoid state leakage between runs.
- **Content scripts run after `document_start` but before `document_idle`** by default — DOM may not be ready. Use `MutationObserver` for DOM-dependent assertions.
- **CSP issues** — some sites (whatnot.com) have strict CSP; injected scripts may be blocked. Test via `chrome.scripting.executeScript` from the SW instead of inline injection.
- **Hot-reload during dev** — if iterating on the extension, use `chrome.runtime.reload()` from a debug script instead of restarting Chrome.

## Output contract

Every test run records to `raw.e2b_run_logs`:

```sql
INSERT INTO raw.e2b_run_logs (
  sandbox_id, task_description, outcome,
  pass_count, fail_count, duration_ms,
  screenshot_urls, console_log_url, vnc_url_archived
) VALUES (...);
```

Append-only — `raw.*` rule from CLAUDE.md.

## Composition with other skills

- Calls `/use-e2b` for sandbox lifecycle.
- Reads `/ask-icps` for "would Patricia/Ben understand this UI?" panel reviews when a test exposes a UX issue.
- Triggers `/lovable-deploy` (when fixed) AFTER tests pass on `main`.

## Failure escalation

| Symptom | First try | Then | Last resort |
|---|---|---|---|
| Test passes locally, fails in E2B | Verify display environment (XVFB), font installation | Add `await page.wait_for_load_state("networkidle")` before assertion | Pin browser version in `/use-e2b` |
| Extension doesn't load | Check `manifest.json` syntax, MV3 compatibility | Verify Chrome version supports MV3 features used | Fall back to MV2 manifest for the test |
| Cookies expired (auth fail) | Rotate Turso `browser_auth:test:*` from a fresh manual login | If no test account, create one + register cookies | Surface VNC for Ben to provision |
| Pool at hard cap | Release stuck claims | Wait 30 min for TTL reaper | Run reduced-scope tests locally only |

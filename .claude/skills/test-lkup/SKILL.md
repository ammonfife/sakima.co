---
name: test-lkup
description: Full E2E browser test suite for lkup.info using 5 ICP personas. Runs Playwright against live site, exercises every user flow (scan, enrich, collections, inventory, settings), collects screenshot proof. 66/70 first-run pass rate.
user-invocable: true
---

@~/.claude/skills/lkup-shared-context/CONTEXT.md

> [!IMPORTANT]
> **Cross-Platform Skill**: This skill is shared across Claude Code, OpenClaw, Gemini, and Codex. 
> Before executing, check the "Platform Blocks" below. If your current platform is missing, or if a command fails due to your unique toolset, **UPDATE THIS SKILL** by adding an `If you are [Platform]...` block detailing how your platform should execute it.

### If you are Claude (Claude Code / OpenClaw)
- Use your native `str_replace_editor` for targeted edits.
- You can spawn background tasks directly using `Bash run_in_background`.

### If you are Gemini (Antigravity / Google)
- Use your native `multi_replace_file_content` or `replace_file_content` tools.
- Background tasks should use the `run_command` tool with `WaitMsBeforeAsync` set appropriately.

### If you are Codex / Grok
- Use your respective file-editing APIs and terminal execution pipelines.


# /test-lkup — Full E2E Test Suite for lkup.info

End-to-end browser testing of lkup.info using 5 ICP personas (Ben, Marcus, Dave, Jess, Patricia), each with unique credentials, cert sets, and test images. Runs Playwright against the live site, exercises every user flow, and collects screenshot proof.

## When to Use

- After deploying new lkup.info features
- Before major releases
- After scan Edge Function changes
- After auth/collection/inventory/settings changes
- When verifying end-to-end enrichment pipeline

## Hard Rules

1. **Screenshot proof required** — HTTP 200 is NOT success. Every test must produce a screenshot showing actual rendered data (description, price, grade).
2. **Fresh enrichment** — Before testing, back up and delete test certs from DB so the full enrichment pipeline fires (not cache hits).
3. **NEVER pause the Supabase database** — even for testing. See memory: `feedback_never_pause_supabase_free_project.md`.
4. **Real barcodes only** — no fake cert numbers. All test inputs come from `test-matrix.json` which uses validated barcodes from `barcode_test_cases.csv`.
5. **Each ICP gets unique login** — `abenfife.<icp>@gmail.com` with password `LkupTest2026!<icp>`.

## Test Matrix

Each of the 5 ICPs tests:

| Flow | What's Verified |
|------|----------------|
| Sign in | Password auth via Supabase API + session injection |
| Manual cert lookup (NGC) | Barcode → scan EF → coin page with description + price |
| Manual cert lookup (PCGS) | Same flow, PCGS enrichment |
| Manual cert lookup (CAC) | CAC 24-digit barcode parsing |
| Manual cert lookup (ANACS) | ANACS barcode detection |
| Manual cert lookup (ICG) | ICG barcode detection |
| Photo upload | Image upload → barcode detection → AI vision fallback |
| Create collection | New collection form → visible in list |
| Batch scan to collection | Scan with `?collection=slug&batch=true` → certs added |
| Browse inventory | `/inventory` page loads with items |
| Dealer margin settings | `/settings/dealer` → change 4 margin fields → save |

**Grader coverage per ICP:** NGC (2 certs), PCGS (2 certs), CAC (1), ANACS (1), ICG (1) = 7 cert lookups + 3 photo uploads + 4 UI flows = 14 tests per ICP.

## Pre-Test Cleanup (Automated)

The test runner backs up and deletes existing test cert data to force fresh enrichment:

```
Tables backed up → deleted (in FK order):
  raw._legacy_raw_coin_observations
  coin_id_review_queue
  draft_listings
  inventory
  coin_xref
  cert_photos
  price_events
  marketplace_listings
  sold_archive
  ebay_listing_xref
  barcode_cert_xref
  grader_data
  pricing_consensus
  certs
```

Backups saved to `lkup.info/test/e2b-icp-tests/backup-*.json`. Restore after testing if needed.

## How to Run

### Prerequisites

- Playwright installed (`npx playwright --version`)
- Supabase keys in keychain (`supabase_lkup_anon_key`, `supabase_lkup_service_role_key`)

### Run all 5 ICPs

```bash
cd ~/github/ammonfife/lkup.info/test/e2b-icp-tests
SUPABASE_ANON_KEY=$(security find-generic-password -s "supabase_lkup_anon_key" -w) \
SUPABASE_SVC_KEY=$(security find-generic-password -s "supabase_lkup_service_role_key" -w) \
node run-icp-test.js all
```

### Run single ICP

```bash
node run-icp-test.js ben    # or marcus, dave, jess, patricia
```

### Run in E2B sandbox

```bash
# Claim a desktop sandbox
SANDBOX_ID=$(curl -s https://e2b-pool-lb.sakima-api.workers.dev/pool/desktop | jq -r '.sandboxId // .sandbox_id')

# Upload test files + run script inside sandbox
# (See run-in-e2b.sh for full orchestration)
```

**Inside the sandbox — connect via CDP, don't launch a new browser:**

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # Chrome already runs on port 9222 in desktop template — connect, don't launch
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # Orient fast — accessibility tree shows all clickable elements in ~5ms
    import json
    print(json.dumps(page.accessibility.snapshot(), indent=2))

    # Click by role/text — no pixel math needed
    page.get_by_role("button", name="Scan").click()
    page.wait_for_load_state("networkidle")
    page.screenshot(path="results/screenshots/ben-scan.png")
```

**Don't pip install — Playwright, xdotool, wmctrl already in desktop template.**

## Output

- **Screenshots:** `test/e2b-icp-tests/results/screenshots/<icp>-<test>.png`
- **Results JSON:** `test/e2b-icp-tests/results/<icp>-results.json`
- **Combined results:** `test/e2b-icp-tests/results/all-results.json`

## Files

| File | Purpose |
|------|---------|
| `test-matrix.json` | ICP credentials, cert assignments, image paths |
| `run-icp-test.js` | Playwright test runner (all flows) |
| `backup-*.json` | Pre-test data backups |
| `results/` | Screenshots + JSON results |

## ICP Personas

| ICP | Email | Persona | Focus |
|-----|-------|---------|-------|
| ben | abenfife.ben@gmail.com | Power dealer | End-to-end production flow |
| marcus | abenfife.marcus@gmail.com | Weekend Whatnot dealer | Mobile-first, speed |
| dave | abenfife.dave@gmail.com | Show booth dealer | Labels, offline, learning curve |
| jess | abenfife.jess@gmail.com | eBay flipper | Margins, comps, speed |
| patricia | abenfife.patricia@gmail.com | Hobbyist collector | Simplicity, free tier |

## Post-Test Restore

To restore backed-up data after testing:

```bash
# Restore certs first, then FK-dependent tables
for table in certs grader_data pricing_consensus barcode_cert_xref inventory coin_xref draft_listings coin_id_review_queue; do
  FILE="backup-${table}.json"
  [ -f "$FILE" ] && curl -s -X POST "${SUPA_URL}/rest/v1/${table}" \
    -H "apikey: ${SVC_KEY}" -H "Authorization: Bearer ${SVC_KEY}" \
    -H "Content-Type: application/json" -H "Prefer: resolution=merge-duplicates" \
    -d @"$FILE"
done
```

## Created

- **Date:** 2026-04-11
- **Context:** ICP-driven E2E testing initiative to validate all lkup.info user flows with screenshot proof
- **Test users created:** 5 Supabase auth accounts (email_confirm=true, password auth enabled)

---
name: test-extensions
description: Comprehensive end-to-end test of every lkup.info browser extension inside an E2B desktop sandbox. Bumps each extension's manifest version (+0.0.1) and commits before every run so Chrome loads fresh code (Chrome caches extension JS aggressively — same-version reload keeps old code). Tests cert-scraping against NGC/PCGS/CAC/ANACS/ICG with rotating known-good certs; tests price-overlay against whatnot.com/ebay.com/google.com/shopping with rotating unique search queries; tests hot-label live-show flow; verifies scrapes actually wrote to Supabase certs/grader_data/coin_xref tables; verifies null-safe protection (Bob iter#173 c2438bef) doesn't clobber existing non-NULL values. Screenshots every unexpected state, documents every failure root cause (no unknown causes), files Turso todos for unresolved issues, writes timestamped log + captains-log summary.
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


# /test-extensions — Browser-extension E2E test suite

Drives every lkup.info Chrome extension through its full test matrix inside an E2B desktop sandbox, verifies real data lands in Supabase, and surfaces every failure with a documented root cause.

The actual driver script is `~/github/ammonfife/lkup.info/scripts/test-extensions.py` — this skill owns the procedure (pre-flight, version bump, commit, run, post-run verification, logging).

## Hard rules (NEVER violate)

1. **Never use Ben's owner browser.** All browser automation runs inside E2B. Never `profile="chrome"`.
2. **Always bump version + commit BEFORE every test run.** Chrome caches extension JS. Same-version reloads frequently keep stale code. Each run gets a fresh patch version. This is non-negotiable per Ben 2026-04-20.
3. **No unknown failure causes.** Every failure documented with root cause in the log. If you can't diagnose it, open a Turso todo with `status=investigating` and a full trace — never silent.
4. **Screenshot + analyze every unexpected state.** Screenshots go in the per-run log dir. Reference them from the markdown log.
5. **No /tmp writes.** All artifacts go to `~/clawd/logs/test-extensions/`, `~/clawd/data/`, or the lkup.info repo.
6. **BIGMAC Hard Rule #1** — any bug found during the run: file Turso todo FIRST, then attempt fix. Close todo only when fix is verified.
7. **Rotate test inputs.** Certs rotated via `~/clawd/data/test-extensions-cert-rotation.json`; queries via `~/clawd/data/test-extensions-query-rotation.json`. Never repeat the same input two runs in a row.
8. **HTTP 200 ≠ working.** Verify scrapes by querying Supabase for actual row updates post-scrape, not just by HTTP status or absence of JS errors.
9. **Patient on page load.** `waitForLoadState('networkidle')` up to 30s. Never barrel through before the DOM is stable.
10. **Screenshot-proof rule.** Per global lkup.info rule: no feature marked passing without a screenshot of it actually working in the live site.

## Extensions covered (as of 2026-04-20)

| Extension | Path | Functions |
|---|---|---|
| lkup.info (unified) | `lkup.info/extension/` | Cert scraping + price overlay + live-show label (everything via one MV3 extension, v1.18.5+) |
| coin-cert-scraper | `auction_tools/browser_extensions/coin-cert-scraper/` | Legacy single-purpose cert scraper (NGC/PCGS/CAC/ANACS/ICG/Gongbo) |
| whatnot-price-overlay-extension | `auction_tools/browser_extensions/whatnot-price-overlay-extension/` | Legacy price overlay (Whatnot + eBay) |
| hot-label | `auction_tools/browser_extensions/hot-label/` | Live-show label print webhook |
| whatnot-inventory-tracker | `auction_tools/browser_extensions/whatnot-inventory-tracker/` | Whatnot inventory capture |

The unified `lkup.info/extension/` covers the same surface as the three legacy extensions combined — treat it as primary. Legacy extensions test as regression baselines.

## Inputs

```bash
/test-extensions                      # full matrix: all extensions, all sites, version-bump + commit, fresh sandbox
/test-extensions --only=unified       # just lkup.info/extension/
/test-extensions --only=coin-cert-scraper,hot-label
/test-extensions --dry-run            # pre-flight only (enumerate + version-bump preview), no sandbox
/test-extensions --no-commit          # skip git commit of version bump (dangerous — breaks Chrome cache-bust invariant)
/test-extensions --headed             # show VNC in browser for visual debug
/test-extensions --reuse-sandbox      # keep previous sandbox instead of fresh one (faster but skips cold-start bugs)
```

## Step 0 — Pre-flight gate

```bash
# Resolve paths
LKUP=~/github/ammonfife/lkup.info
AUCTION=~/github/ammonfife/auction_tools
DRIVER=$LKUP/scripts/test-extensions.py
LIB=~/.claude/skills/test-extensions/lib
LOG_ROOT=~/clawd/logs/test-extensions

[ -f "$DRIVER" ] || { echo "FAIL: driver $DRIVER missing"; exit 1; }
[ -d "$LIB" ]    || { echo "FAIL: skill lib $LIB missing"; exit 1; }

# Working tree must be clean for lkup.info (we're going to commit a version bump to it)
cd $LKUP
if ! git diff --quiet HEAD && [ "$ALLOW_DIRTY" != "1" ]; then
  echo "FAIL: lkup.info working tree dirty — commit or stash first (or ALLOW_DIRTY=1)"
  git status --short
  exit 1
fi

# E2B token
[ -n "$E2B_API_KEY" ] || E2B_API_KEY=$(security find-generic-password -s E2B_API_KEY -a benfife -w 2>/dev/null)
[ -n "$E2B_API_KEY" ] || { echo "FAIL: E2B_API_KEY not in keychain"; exit 1; }

# Supabase DB password (for post-scrape verification)
SUPA_PW=$(security find-generic-password -s supabase_lkup_db_password -w 2>/dev/null)
[ -n "$SUPA_PW" ] || { echo "FAIL: supabase_lkup_db_password not in keychain"; exit 1; }

# psql binary (Supabase CLI is blocked on cli_login_postgres per iter #51+)
PSQL_BIN=/opt/homebrew/opt/libpq/bin/psql
[ -x "$PSQL_BIN" ] || PSQL_BIN=$(which psql)
[ -x "$PSQL_BIN" ] || { echo "FAIL: no psql"; exit 1; }

# Run id
RUN_ID=$(date -u +%Y-%m-%dT%H-%M-%SZ)
RUN_LOG_DIR=$LOG_ROOT/$RUN_ID
mkdir -p "$RUN_LOG_DIR"/{screenshots,console,supabase}
```

## Step 1 — Enumerate + version-bump all targeted extensions

`lib/bump-versions.sh` walks every extension's `manifest.json`, bumps the patch segment by `+0.0.1`, writes the new value back atomically, appends a `CHANGELOG.md` entry, and returns the old→new map as JSON.

```bash
bash $LIB/bump-versions.sh --only="$ONLY" --run-id="$RUN_ID" > $RUN_LOG_DIR/version-bumps.json
cat $RUN_LOG_DIR/version-bumps.json
```

Example output:

```json
{
  "run_id": "2026-04-20T19-42-03Z",
  "bumps": [
    {"path":"lkup.info/extension/manifest.json","old":"1.18.5","new":"1.18.6"},
    {"path":"auction_tools/browser_extensions/coin-cert-scraper/manifest.json","old":"1.3.2","new":"1.3.3"},
    {"path":"auction_tools/browser_extensions/whatnot-price-overlay-extension/manifest.json","old":"2.3.3","new":"2.3.4"},
    {"path":"auction_tools/browser_extensions/hot-label/manifest.json","old":"1.6.5","new":"1.6.6"},
    {"path":"auction_tools/browser_extensions/whatnot-inventory-tracker/manifest.json","old":"1.0.0","new":"1.0.1"}
  ]
}
```

## Step 2 — Commit version bumps

```bash
# lkup.info commit
cd $LKUP
git add extension/manifest.json extension/CHANGELOG.md 2>/dev/null || true
git commit -m "test-extensions $RUN_ID: version bump for cache-bust" -m "Ben 2026-04-20 hard rule: every test run bumps version + commits to force Chrome fresh load" || echo "no lkup.info bump this run"
git push origin main

# auction_tools commit (separate repo)
cd $AUCTION
git add browser_extensions/*/manifest.json browser_extensions/*/CHANGELOG.md 2>/dev/null || true
git commit -m "test-extensions $RUN_ID: version bump for cache-bust" || echo "no auction_tools bump this run"
git push origin main 2>/dev/null || echo "auction_tools push failed — recording locally only (known push-blocked state OK)"
```

`--no-commit` skips this step but surfaces a loud warning in the log. Chrome's cache-bust invariant is broken without the commit — document it.

## Step 3 — Rotate test inputs

`lib/rotate-certs.sh` picks 3–5 fresh certs per grader from `public.certs` (excluding any cert used in the last 2 runs) and writes the selection to `$RUN_LOG_DIR/certs.json`. Rotation history lives at `~/clawd/data/test-extensions-cert-rotation.json` (deduped rolling window of last 20 runs).

`lib/rotate-queries.sh` picks 5 fresh eBay/Whatnot/Google-Shopping search queries from a seed list (`lib/query-seed.json`) plus random variations, excluding any query used in the last 2 runs. Writes to `$RUN_LOG_DIR/queries.json`; history at `~/clawd/data/test-extensions-query-rotation.json`.

```bash
bash $LIB/rotate-certs.sh   --count=5 --out=$RUN_LOG_DIR/certs.json
bash $LIB/rotate-queries.sh --count=5 --out=$RUN_LOG_DIR/queries.json
```

## Step 4 — Claim E2B desktop + load extensions

Pool-first per global policy:

```bash
SBX_JSON=$(curl -s https://e2b-pool-lb.sakima-api.workers.dev/pool/desktop)
SBX_ID=$(echo "$SBX_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('sandboxId',''))")
[ -z "$SBX_ID" ] && { echo "pool empty — spinning new"; sbx new bigmac-desktop-v3-0-0; SBX_ID=$(sbx ls | awk '/desktop/{print $1; exit}'); }
echo "$SBX_ID" > $RUN_LOG_DIR/sandbox-id
```

Driver opens Chromium with `--load-extension=<path1>,<path2>,...` and the realistic headers Ben specified:

```
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15
Accept-Language: en-US,en;q=0.9
Sec-Ch-Ua: "Not/A)Brand";v="99", "Chromium";v="131"
Sec-Ch-Ua-Mobile: ?0
Sec-Ch-Ua-Platform: "macOS"
Referer: <appropriate per page>
```

DevTools console capture on — every `page.on('console', ...)` event streams to `$RUN_LOG_DIR/console/<site>-<n>.log`.

## Step 5 — Run test matrix

The driver runs each matrix row in sequence, capturing screenshots + console logs + Supabase post-snapshots:

### 5a. Cert scraping (unified + coin-cert-scraper)

For each (grader, cert) in `certs.json`:
1. Navigate to grader cert page (NGC: `ngccoin.com/certlookup/<cert>/`, PCGS: `pcgs.com/cert/<cert>`, etc.)
2. `waitForLoadState('networkidle')` up to 30s
3. Screenshot full page → `screenshots/cert-<grader>-<cert>.png`
4. Capture DevTools console → `console/cert-<grader>-<cert>.log`
5. Wait up to 15s for extension to write via scan EF
6. Query Supabase:
   ```sql
   SELECT id, coin_id, grade, service, updated_at, description
   FROM public.certs WHERE id = '<GRADER>-<cert>' ORDER BY updated_at DESC LIMIT 1;
   SELECT cert_id, source, fetched_at FROM public.grader_data WHERE cert_id = '<GRADER>-<cert>'
   ORDER BY fetched_at DESC LIMIT 5;
   ```
7. Verify `updated_at` is within last 60s (proves fresh write) AND grade/description are non-null.
8. **Null-safe check** (Bob iter#173 c2438bef): re-scrape same cert, confirm no existing non-NULL value was clobbered. Compare before/after snapshot of non-null fields — they must match byte-for-byte.

### 5b. Price overlay (unified + whatnot-price-overlay)

For each (site, query) in `queries.json`:
1. Navigate to site search URL (whatnot.com/browse?query=..., ebay.com/sch/?nkw=..., google.com/search?tbm=shop&q=...)
2. `waitForLoadState('networkidle')` up to 30s
3. Screenshot → `screenshots/overlay-<site>-<idx>.png`
4. DOM check: overlay element present (`[data-lkup-overlay]` or extension-injected div)
5. Verify at least 1 listing has consensus price rendered from the overlay
6. If Cloudflare/CAPTCHA: screenshot the block page, try alternate path (different query, different UA header combo) before declaring blocked.

### 5c. Hot-label (live-show)

1. Navigate to a known Whatnot live show URL from `lib/known-shows.json`
2. Wait for label webhook wiring (extension registers MutationObserver on purchase events)
3. Simulate purchase event by injecting a synthetic DOM mutation via `browser_evaluate`
4. Verify webhook fired (check Supabase `raw.label_print_events` for a row in the last 60s, OR check local print queue if configured)

### 5d. Whatnot inventory tracker

1. Navigate to `whatnot.com/sakima/inventory` (or similar — driver discovers via manifest)
2. Wait for extension to populate inventory panel
3. Verify inventory data matches a control sample from `public.inventory WHERE owner_user_id = <sakima>`

## Step 6 — Post-run verification + report

Driver writes a markdown report at `$RUN_LOG_DIR/REPORT.md` with:

- Extensions tested (name, old version, new version)
- Test inputs used (certs, queries)
- Per-test pass/fail (link to screenshot + console log + Supabase snapshot)
- Failure root causes (never "unknown" — if undiagnosed, status=investigating + Turso todo)
- Resolutions attempted (header changes, retries, fresh sandbox)
- Total pass/fail counts
- Sandbox ID + VNC URL for forensics

## Step 7 — Turso todos for anything unresolved

For every failed test with no successful resolution, file a Turso todo:

```bash
TURSO_URL="libsql://bigmac-ammonfife.aws-us-west-2.turso.io"
TOK=$(security find-generic-password -a bigmac -s turso-bigmac-token -w)
turso db shell "$TURSO_URL?authToken=$TOK" "
  INSERT INTO todos (task, priority, tags, assigned_to, status)
  VALUES (
    '<concise description + root cause + suggested fix>',
    '<high|medium|low>',
    'test-extensions,<extension-name>,<run-id>',
    'claude',
    'investigating'
  );
"
```

Per BIGMAC Hard Rule #1 — filed FIRST. If the agent then fixes the issue in-session, close the todo with `todo done <id>` after verification.

## Step 8 — Captain's log entry

```bash
~/bin/captains-log add \
  --topic="test-extensions run $RUN_ID" \
  --type=milestone \
  --summary="Ran full extension test suite. Extensions: <list>. Pass: <N>/<total>. New versions committed: <list>. Findings: <1-2 sentence summary>. Todos filed: <list of ids>. Report: $RUN_LOG_DIR/REPORT.md" \
  --files="$RUN_LOG_DIR/REPORT.md" \
  --commits="lkup.info@<sha>:version bump,auction_tools@<sha>:version bump" \
  --tags="test-extensions,browser-ext,e2b,cache-bust"
```

## Step 9 — Output summary

```
✅ /test-extensions complete
   Run ID:         $RUN_ID
   Extensions:     <n> bumped to <versions>
   Pass/Fail:      <p>/<f>
   Commits:        lkup.info@<sha>, auction_tools@<sha>
   Todos filed:    <count> (#<id1>, #<id2>...)
   Report:         $RUN_LOG_DIR/REPORT.md
   Sandbox:        $SBX_ID (VNC: <url>)
```

## Anti-patterns (never do)

- Run without version bump + commit — Chrome cache-bust invariant broken
- Repeat same cert or query two runs in a row — rotation is mandatory
- Skip Supabase post-verification — HTTP 200 ≠ working
- Log "unknown error" — every failure has a root cause. If genuinely unknown, `status=investigating` on the todo, not silent failure
- Use Ben's local Chrome profile — E2B only
- Skip screenshots on unexpected states — mandatory proof
- Delete old rotation history files — they're the "don't repeat" guarantee

## Related skills

- `/use-e2b` — underlying sandbox automation (this skill delegates to it)
- `/update-extension` — single-extension version bump (this skill multi-bumps across all)
- `/test-lkup` — parallel full-site E2E (extension tests are complementary, not redundant)
- `/price-coins` — cert→price workflow the extensions feed into
- `captains-log` — summary entry at end

## Files owned by this skill

- `/Users/benfife/.claude/skills/test-extensions/SKILL.md` (this file)
- `/Users/benfife/.claude/skills/test-extensions/lib/bump-versions.sh`
- `/Users/benfife/.claude/skills/test-extensions/lib/rotate-certs.sh`
- `/Users/benfife/.claude/skills/test-extensions/lib/rotate-queries.sh`
- `/Users/benfife/.claude/skills/test-extensions/lib/query-seed.json`
- `/Users/benfife/.claude/skills/test-extensions/lib/known-shows.json`
- `/Users/benfife/.claude/skills/test-extensions/README.md`
- `/Users/benfife/github/ammonfife/lkup.info/scripts/test-extensions.py` (driver)

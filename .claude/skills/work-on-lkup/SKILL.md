---
name: work-on-lkup
description: "Meta-skill for working on lkup.info. Updated 2026-04-13. Supabase Pro + 25 Edge Functions (8,897 LOC) + 10 CF Workers (1,609 LOC) + extension v1.12.0 + 3-method parallel enrichment + pricing_consensus supersession + coin-vision + SMS. See UPDATES-2026-04-13.md for cross-repo overlap map."
---

@~/.claude/skills/lkup-shared-context/CONTEXT.md

# /work-on-lkup

Meta-skill. Read this before doing anything in `~/github/ammonfife/lkup.info` or its extension, edge functions, or operator dashboards.

**Goal of this skill**: an agent picks up a task, reads this, learns the architecture, learns which sub-skills handle which kind of work, learns the DO-NOTs, and starts from the current state instead of rediscovering what already exists.

**IMPORTANT:** Also read `UPDATES-2026-04-13.md` in this skill directory for the latest cross-repo overlap map, updated counts, and gap status.

---

## 🛑 Before you touch anything

1. **Read `lkup-plan.json`** at the repo root. That's the living architecture plan (currently at v5.37). It has the policies, the URL rules, the schema, the consolidation plan, the stubs roadmap, and the merge freezes. Not optional.
2. **Do not reinvent the wheel.** Almost every scraping, enrichment, or pricing path you're about to build already exists in some form. Check `functions/` (Supabase Edge Functions), `supabase/functions/`, `cloudflare/` (workers), `extension/content/` (browser content scripts), and `api-python/` (legacy Flask — do NOT add new code here).
3. **Do not backwash on old decisions.** The plan has marked things like "Cloud Run is sunset", "E2B is currently secondary", "never delete, migrate only", "never mark anything completed without a screenshot", and a dozen similar directives. If you're tempted to do the opposite of one of those, STOP and re-read the plan's relevant section.

---

## The current working system (updated 2026-04-13)

**Frontend:**
- React 18 + TypeScript + Vite SPA at `~/github/ammonfife/lkup.info/src/` — 33 pages
- Deployed via **Lovable.dev** — git push → Lovable auto-fetches → **Publish button must be clicked** → Vercel builds → `lkup.info` live. Git push alone does NOT deploy. Lovable deploy unblocked as of 2026-04-13.
- Routes of note: `/obs` (OBS overlay), `/coin/...` (full coin page), `/scan` (web scanner), `/dealer/:slug` (storefront), `/settings` (enrichment mode)
- **iOS app**: Capacitor 8.2.0 wrapper (Bundle ID: `com.sakima.lkup`, min iOS 16.0). Same React codebase.

**Backend — canonical data spine:**
- **Supabase** = `https://vsotvatntzlrzrhemayh.supabase.co`. PostgreSQL + Auth + Realtime + Edge Functions. **Pro tier** ($25/mo, upgraded 2026-04-13).
- Three schemas: `reference.*` (third-party coin info, read-mostly, NOT exposed via PostgREST), `raw.*` (append-only firehose, exposed via `Accept-Profile: raw` header), `public.*` (canonical sanitized data, default schema).
- React reads from `public.*` only. Enrichment writes to `raw.*`. Reference schema only accessible via service_role inside Edge Functions.

**Edge Functions** (`functions/` dir in the repo — deploy with `supabase functions deploy <name>`):
All 25 Edge Functions (8,897 LOC total). Key functions:
- `scan` (v127, 3212 lines) — THE canonical barcode-to-data entry. Includes Quick Actions + parse mode for ICG/CAC/ANACS scrapers.
- `enqueue-enrichment` (v39, 737 lines) — fire-and-forget enrichment. Uses `upsert_pricing_consensus()` RPC. Video_url idempotency guard.
- `talking-points` (v39, 740 lines) — AI auction pitch. Claude OAuth primary, Lovable secondary, Gemini fallback.
- `price-guide` (v18, 379 lines) — eBay sold comp lookup. Uses `upsert_pricing_consensus()` RPC.
- `obs-state`, `gongbo-enrich` (402 lines), `listing-draft`, `ebay-publish`, `ebay-sold-webhook`, `ebay-listings-sync` (356 lines)
- `whatnot-sale-ingest`, `capture-whatnot`, `scrape-whatnot-dealer` (643 lines)
- `sms-inbound` (v2) / `sms-outbound` (v2) — Photo-based coin onboarding via SMS (NOT the Surge.app keyword service — that's `sakima-sms` on Cloud Run)
- `coin-id-bridge`, `coin-action`, `bulk-image-zoom`, `generate-video`, `lot-scan`
- `db-fix`, `flags` (stub), `learn-selectors`, `mirror-image`

**Cloudflare Workers** (10 workers, 1,609 LOC total, deploy with `wrangler deploy`):
- `e2b-pool-lb-cf` — E2B sandbox pool load balancer (D1-backed, hard cap 60, 30min TTL).
- `gongbo-scraper` (271 lines) — Chinese coin scraper. Template for all CFBR scrapers.
- `ngc-scraper` (91 lines) — NGC cert scraper (Quick Actions).
- `icg-scraper` (127 lines) — ICG cert scraper (parse mode).
- `cac-scraper` (70 lines) — CAC cert scraper (parse mode).
- `anacs-scraper` (87 lines) — ANACS cert scraper (parse mode).
- `segs-scraper` (106 lines) — SEGS cert scraper.
- `coin-vision` (179 lines) — Real-time coin ID from video via Gemini 2.5 Flash.
- `greysheet-scraper` (581 lines) — Greysheet price guide scraper.
- `pcgs-api-proxy` (97 lines) — PCGS API token proxy.

**Enrichment architecture (3-method parallel, updated 2026-04-11):**
All 7 grading services fire up to 3 methods in parallel:
- PCGS: API → E2B | NGC: Direct HTTP → CF Browser → E2B | ICG: Direct HTTP → CF Interactive
- CAC: CF Browser → E2B | ANACS: CF Interactive → E2B | SEGS: CF Interactive → E2B | Gongbo: CF Browser
- **pricing_consensus** — append-only with supersession. `is_current` BOOLEAN + `superseded_at`. All writes via Postgres RPC `upsert_pricing_consensus()`. Extended with ebay_min/max/avg/second/count + whatnot_min/max/avg/count.
- **CFBR** is the primary scraping path. 5 dedicated per-grader CF Workers deployed.
- **Cookie injection**: Turso `browser_auth:*` cookies.
- **E2B Sandboxes** — architecturally preferred, currently secondary. Pool-lb CF Worker is the only valid claim path.

**AI backends for content generation:**
- **PRIMARY: Claude OAuth** (Sonnet 4.5 via Ben's Claude Max subscription, zero per-call cost). Token in keychain at `claude_code_oauth_token_ammonfife`, set as Supabase secret `CLAUDE_OAUTH_TOKEN`. **Headers must match Claude CLI exactly**: `anthropic-beta: claude-code-20250219,oauth-2025-04-20`, `anthropic-version: 2023-06-01`, `User-Agent: claude-cli/2.1.89 (external, cli)`, `x-app: cli`. Missing any = 401.
- **Secondary: Lovable AI Gateway** (Lovable credits).
- **Fallback: direct Gemini 2.5 Flash** (Google AI API key).

**Image storage:**
- **R2 mirror** at `https://pub-9a3e595d93554c6b8c74c009fe3309a7.r2.dev/coins/<cert_id>/<obverse|reverse>.jpg`. Not every cert is mirrored yet — render pattern is: try R2 first, `<img onerror>` fallback to OG NGC/PCGS CDN URL.

**Operator tooling:**
- `~/github/ammonfife/lkup.info/tools/obs-control.html` — operator dashboard. Recent scans feed, filters, search, barcode input, Show Price/Video toggles, OPEN ↗ links, Whatnot popup launcher.
- `~/github/ammonfife/lkup.info/tools/obs.html` — local mirror of the OBS overlay (fixed width 1200px, variable height, upscaled 2.5×). Use when Lovable publish is backed up and the deployed `/obs` route hasn't caught up.
- Served by `python3 -m http.server 6768 --directory ~/github/ammonfife/lkup.info/tools --bind 127.0.0.1`.

**Extension:**
- `~/github/ammonfife/lkup.info/extension/` — the unified `lkup.info` Chrome extension (**v1.12.0**, MV3, 12 content scripts). Features: cert scraping, price overlay, auction-labels, auth bridge, snap panel, frame-unbust, context menus, eBay import, SEGS extractor, auto-print, consensus price overlay, cert history. **Load unpacked** in Chrome dev mode.
- **Extension evolution:** v1.7.0 (auto-print), v1.8.0 (context menus + eBay import), v1.9.0 (`<all_urls>` perms), v1.10.x (cert history), v1.12.0 (Quick Actions NGC scraper).
- Source extensions being lifted: `~/github/ammonfife/auction_tools/browser_extensions/coin-cert-scraper/` (v1.3.1), `~/github/ammonfife/auction_tools/browser_extensions/whatnot-price-overlay-extension/` (v2.4.0), and `~/hot-label-sakima/` (Sakima local version of hot-label, no cloud dependency).
- **Auction-labels** (formerly hot-label): `~/hot-label-sakima/watcher_injected.js` hooks `WebSocket.prototype` to sniff Whatnot's Phoenix channels (`commerce:payment_succeeded`, `auction_ended`, `giveaway_won`). Prints sale receipt labels on thermal printer (QZ Tray bridge) for post-stream packaging. NOT shipping labels — buyer username + item title + lot# + price labels.

**Shared TypeScript modules** (`shared/`):
- `barcode-parser/` — canonical barcode parser (22+ services, 34-row test fixture, PARSING_LOGIC.md lineage doc). 3-way sync with `api-python/libs/barcode_parser/` and `functions/scan/index.ts`.
- `scan-input/` — NEW (2026-04-09). Unified orchestrator. `parseInput()` routes any input (barcode, QR, URL, text) to the right sub-parser, normalizes to `UnifiedScanResult`. Types: `InputModality`, `ObjectType`, `UnifiedScanResult`.
- `coin-parser/` — `parseCoinTitle()` extracts year, grade, service, denomination from text descriptions. 40+ coin types.
- `pricing/` — Margin calculation, melt calc, consensus logic.

**Feature manifest:**
- `homepage-features.json` — machine-readable JTBD audit of all 32 features promised/built. Each feature tagged with status (working/partial/broken/not_built), implementation path, and gap analysis. Readable by bots/agents for prioritization.

**Documentation architecture:**
- `lkup-plan.json` (400KB) — THE canonical plan. Being split into satellite files (gaps, version_history, schema → `plan/*.json`).
- `CLAUDE.md` — agent context-window cache. Intentionally duplicates plan sections. Must stay SYNCED, not deduplicated.
- `instructionsforbob.md` — DEPRECATED. Migrating to Turso `AGENT_CONTEXT.md` via `claude-sync pull`. Use Turso facts with `scope:agent:bob` tag instead.
- `BOB_CHANNEL.md` — stays. Task queue between Bob and Lovable.
- `supabase/reference/` — schema maps, parity audits, linked accounts design.

---

## When to use which sub-skill

| Task | Use skill |
|---|---|
| Price a coin / verify a cert / understand the sold-comps pipeline | **`/price-coins`** |
| Port a Python module from `auction_tools/` to TypeScript in `lkup.info/shared/` | **`/lift-module`** |
| Verify a ported TS module matches the Python original | **`/audit-parity`** |
| Fix a broken TODO stub or frontend-backend URL mismatch | **`/fix-stubs`** (Phase 0) |
| Run the full consolidation pipeline phase-by-phase | **`/consolidate`** |
| Validate proposed code changes against `lkup-plan.json` policies | **`/plan-validator`** (run before every commit) |
| Edit `lkup-plan.json` itself | **`/lkup-plan-editor`** (the single canonical writer) |
| Push a frontend deploy via Lovable | **`/lovable-deploy`** |
| Build a knowledge graph of the codebase | **`/graphify`** |
| Rewrite-prone domain (multiple impls, recurring regressions) | **`/lift-and-constrain`** — inventory → nuance harvest → test fixture → canonical impl |
| You think you're "blocked" on something non-trivial | **`/lift-and-constrain`** (Turso policy #758 — "blocked" triggers subagent exploration) |

---

## HARD DO-NOTs

These are non-negotiable. Violating any of them triggers a Garcia policy correction.

1. **NEVER disable features to silence errors.** Fix the root cause. No --no-verify, no --max-instances=0, no comment-outs, no disconnecting CI/CD, no skipping tests to make them pass. (Policy: "Fix root causes, not symptoms.")
2. **NEVER delete without explicit permission.** Migrate, deprecate, rename — but don't delete rows, tables, branches, files, Cloud Run services, or sandboxes without Ben explicitly saying "delete X". Two-table data migrations are COPY only, never cutover-by-delete.
3. **NEVER write synthetic data to production tables to satisfy a screenshot.** If the pipeline can't produce the real data, mark PENDING or fix the upstream. Don't backfill fake rows.
4. **NEVER touch `desktop_scanner.py` without extreme care.** It's 18k lines, actively co-developed, and "MUST NOT BREAK." Any change must be surgical, additive when possible, and tested immediately.
5. **NEVER add new code to `api-python/` (Cloud Run).** It's being sunset to eliminate the last GCP dependency. New enrichment → Supabase Edge Functions.
6. **NEVER add Google Cloud dependencies.** lkup.info is migrating AWAY from GCP. New services go to Supabase or Cloudflare.
7. **NEVER modify `src/components/ui/*`.** Those are shadcn primitives — upstream source, off-limits.
8. **NEVER UPDATE or DELETE rows in `raw.*` tables.** Append-only firehose.
9. **NEVER migrate price columns.** Pricing comes from clean sources (PCGS guide / eBay sold / Edge Fn live), never from legacy SQLite columns.
10. **NEVER call `Sandbox.create()` from consumer code.** Always claim from the pool-lb CF Worker. Direct create is the exact pattern that caused the 2026-04-06 E2B leak.
11. **NEVER mark anything completed without a screenshot.** Global lkup.info policy per `lkup-plan.json` v5.19+. Code pushed ≠ done. Deployed ≠ done. Screenshot of working feature = done.
12. **NEVER treat HTTP 200 as "working".** Parse the body, verify expected fields. A 200 with stub data is NOT evidence of a working pipeline.
13. **NEVER say "never" to E2B.** E2B is architecturally preferred and is a valid fallback at every layer. It's currently in a blocked state, not deprecated. Preserve it in code and policy.

---

## Current in-flight gaps (updated 2026-04-13)

See `UPDATES-2026-04-13.md` in this skill directory for the complete gap list. Key items:

1. **melt_value pipeline broken** — 0 coverage. `pricing_rollup.py` needs fixing.
2. **Consensus-equals-melt bug** — upstream rollup fallback still wrong for commemoratives/world coins.
3. **R2 image backfill** — 298 migrated (2026-04-09), not running continuously.
4. **Gongbo modal bypass** — CF Worker deployed but Chinese legal terms modal unreliable.
5. **Locked prices deployed** — `locked_prices` table + view + 12 rows (migration 20260409000001). Enrichment respects lock-only-upward.
6. **Talking-points cache** — still no version column.
7. ~~**Lovable publish backlog**~~ — **RESOLVED 2026-04-13.** All queued commits live.
8. **E2B secondary** — pool-lb CF Worker is the only valid claim path. CFBR is primary scraping.
9. **18.5M REST requests/week** — usage monitoring needed on Pro tier.
10. **pricing_consensus + coin_xref RLS** — P0 fixes deployed (commits 63c763b3, df6a4fc6). 1,751 + 42,701 rows unlocked.
11. **Phase 1 consolidation DONE** — barcode-parser, coin-parser, pricing all ported to TypeScript.
12. **Capacitor camera error on iOS** — under investigation.

---

## Canonical file locations

| File | Purpose |
|---|---|
| `lkup-plan.json` | THE living architecture plan (v5.34+). Read first. |
| `instructionsforbob.md` | Bob's Lovable agent operating guide |
| `BOB_CHANNEL.md` | Task queue between Bob and Claude |
| `LOVABLE.md` | Product spec — pages, design, business rules |
| `tools/obs-control.html` | Operator dashboard (served on localhost:6768) |
| `tools/obs.html` | Local OBS overlay mirror |
| `functions/talking-points/index.ts` | Talking-points Edge Function v4 |
| `functions/price-guide/index.ts` | eBay comp lookup Edge Function |
| `functions/scan/index.ts` | Barcode → cert → enrichment pipeline Edge Function |
| `functions/obs-state/index.ts` | OBS overlay state storage |
| `functions/gongbo-enrich/index.ts` | Chinese coin scraper (STUB) |
| `extension/manifest.json` | Unified lkup.info Chrome extension manifest |
| `src/pages/OBSOverlay.tsx` | Deployed OBS overlay React component |
| `src/pages/Coin.tsx` | Full coin detail page |

---

## Running the dashboards right now

```bash
# Operator dashboard + local overlay mirror (localhost:6768)
cd ~/github/ammonfife/lkup.info/tools
nohup python3 -m http.server 6768 --bind 127.0.0.1 >/tmp/obs-control-server.log 2>&1 &

# Open everything
open 'http://localhost:6768/obs-control.html'   # operator control panel
open 'http://localhost:6768/obs.html'           # local overlay (point OBS Browser Source here)
open 'https://lkup.info/obs'                    # deployed overlay (after Lovable publish)
```

---

## Deploying changes

```bash
# Edge Function
cd ~/github/ammonfife/lkup.info
supabase functions deploy <function-name> --no-verify-jwt

# After a prompt change, always nuke the relevant cache table
SRK=<service role key from keychain>
curl -sS -X DELETE "https://vsotvatntzlrzrhemayh.supabase.co/rest/v1/talking_points_cache?cert_id=not.is.null" \
  -H "apikey: $SRK" -H "Authorization: Bearer $SRK"

# Frontend (React + extension) — via Lovable
git add <files>
git commit -m "..."
git push origin HEAD
# Then click Publish in the Lovable UI, OR:
# /lovable-deploy  (runs the publish via E2B desktop + Playwright)

# Supabase secrets (e.g. CLAUDE_OAUTH_TOKEN)
echo "KEY=value" > /tmp/env
supabase secrets set --env-file /tmp/env
rm /tmp/env
```

---

## Auth tokens + where they live

| Token | Location | Used by |
|---|---|---|
| Supabase anon JWT | `src/lib/supabase.ts` (hardcoded), env `VITE_SUPABASE_ANON_KEY` | React + all client-side code |
| Supabase service role JWT | Edge Function env `SUPABASE_SERVICE_ROLE_KEY` | Edge Functions only |
| Claude OAuth token | Keychain `claude_code_oauth_token_ammonfife`, Supabase secret `CLAUDE_OAUTH_TOKEN` | talking-points Edge Fn |
| Gemini API key | Edge Function env `GOOGLE_AI_API_KEY` | talking-points fallback + other AI functions |
| PCGS API token | Keychain `pcgs_api_token` | PCGS cert lookups |
| Cloudflare API token | `gcloud secrets versions access latest --secret=cloudflare_api_token --project=heimdall-8675309` | CFBR requests |
| Turso bigmac token | Keychain `turso-bigmac-token` | Fact store (shared across agents) |
| eBay OAuth | Nightly refresh via `ebay_comp_refresher.py` | eBay Browse API |

---

## Sibling skills to know about

- `/price-coins` — full pricing workflow (read first for any pricing task)
- `/lift-module` — Python → TypeScript porting
- `/audit-parity` — verify ported modules
- `/fix-stubs` — wire broken TODOs
- `/plan-validator` — validate against lkup-plan.json
- `/lkup-plan-editor` — edit the plan itself
- `/consolidate` — run phase-by-phase consolidation
- `/lovable-deploy` — push frontend to production
- `/graphify` — knowledge graph of the codebase

---

## Common pitfalls (hit every one in production, documented so you don't)

1. **Description too thin for eBay search** — `"1887 $1"` returns 0 comps, `"1887 Morgan Dollar"` returns 28. Always expand via `expandDescription()` before calling `price-guide`.
2. **Cert variant mismatch** — same coin exists as `NGC-8647036-022` AND `NGC-8647036022`. Fetch both variants, pick the enriched one.
3. **consensus_price == melt_value** — upstream rollup broken fallback. Detect client-side and override with price-guide eBay data.
4. **Talking-points cache stale after prompt edit** — cache is cert_id-keyed with no version column. Every prompt change = manual DELETE from `talking_points_cache`.
5. **Claude OAuth token expired** — Claude Code CLI rotates tokens frequently. Keychain entry `Claude Code-credentials` expires every ~8h. Use `claude_code_oauth_token_ammonfife` (fresher) or refresh via `claude` CLI.
6. **Missing Claude headers = 401** — `anthropic-beta: claude-code-20250219,oauth-2025-04-20` is required. Missing the `claude-code-20250219` prefix alone = authentication_error.
7. **price-guide returns `low: 0, high: 0`** — means no eBay comps found for that query. Not a bug. Expand the description or skip the price beat.
8. **Gemini hallucinates populations and auction prices** — add explicit KNOWN_FACTS + MISSING_DATA blocks to the prompt. Gemini invents "only 3 finer at NGC" if you don't tell it not to.
9. **Gemini adopts stock LLM phrases** ("represents a superb example", "leveraging current price guides", "emerged during the height of") unless the prompt explicitly bans them.
10. **Gemini spells numbers as words** ("one-fifty-seven") when asked for phonetic pronunciation. Explicitly say "numerals only, never spell as words".
11. **Gemini over-pronounces common names** ("George T. Morgan [MOR-gan]"). Explicit skip list for Morgan, Lincoln, Liberty, Eagle, Dollar, etc.
12. **OBSOverlay.tsx poll returned 401** before commit `4e63707` — the fetch had no auth headers. Gateway returns 401, coin stays null, `if (!coin) return null;` renders empty body, OBS sees white. Always send anon JWT + apikey on Edge Function GETs.
13. **OBS sees white even when overlay has data** — React default body background is white. Force `html, body, #root { background: transparent }` on mount (and restore on unmount for other routes).
14. **Whatnot iframe logs you out** — JS frame-busting detects top !== self and kills the session. Content script at `document_start` in MAIN world redefining `window.top === window.self` defeats it, scoped to localhost:6768 + lkup.info parent origins.
15. **USB HID barcode scanner types into wrong field** — autofocus the barcode input on page load and refocus on any non-input click. Password managers hijack autofocus unless you use `type="search"` + `data-lpignore` + `data-1p-ignore` + `data-form-type="other"` + an obscure name.
16. **Direct `Sandbox.create()` triggers E2B leak** — 2026-04-06 incident cost $1,949 in 30d. ONLY claim from `e2b-pool-lb.sakima-api.workers.dev/pool/{code,desktop}`. Consumer code NEVER creates directly.
17. **Cloudflare Worker `lkup-api.sakima-api.workers.dev` returns `error 1042`** — DNS not proxied yet. Not a working endpoint as of 2026-04-08.
18. **Cloud Run `coin-price-proxy` returns `"All enrichment methods failed"`** — legacy path is broken downstream of the E2B blocked state. Not a viable fallback. Don't route to it.
19. **`reference.*` schema is NOT exposed via PostgREST** — only `public`, `graphql_public`, `raw`. Reference tables only accessible via service_role inside Edge Functions OR by creating a `public.*` view wrapper.
20. **`raw.*` tables have weird column names** — `raw.cert_scrapes` uses `scraped_at` not `created_at`, `raw.coin_observations.coin_id` is a UUID not a cert_id string. Probe schema before writing queries.
21. **`public.talking_points_cache` cert_id must match exactly** — if you push hyphenated, lookup hyphenated; if flat, flat. No variant resolution at the cache layer.
22. **Gongbo data is behind a Chinese legal-terms modal** — CFBR's generic button-click actions don't match. Need specific Chinese text click target OR mobile app API reverse-engineering.
23. **Lovable deploys are manual** — git push ≠ deploy. Click the Publish button in Lovable UI OR run `/lovable-deploy`. Lovable auto-fetches but doesn't auto-publish.
24. **Supabase Edge Function deploys need the CLI**, not git — `supabase functions deploy <name> --no-verify-jwt`. Note: the CLI uses `supabase/functions/` directory, but hardlinked to `functions/` in this repo so edits to either propagate.
25. **Supabase gateway requires auth header even for "public" Edge Functions** — `no-verify-jwt` means the function itself doesn't check JWT, but the gateway still requires `apikey: <anon>` + `Authorization: Bearer <anon>`. Without it → 401.
26. **Edge Functions writing to `raw.*` schemas MUST use `SUPABASE_SERVICE_ROLE_KEY`** — NOT the anon key + RLS policy + GRANT INSERT. Confirmed 2026-04-09 on `whatnot-sale-ingest`: RLS anon INSERT policy + table GRANT + schema USAGE all applied and curl still returned `permission denied for table whatnot_sales`. Service role bypasses PostgREST's extra permission stack on raw schemas. Pattern matches `sms-inbound/index.ts`. Same applies to `raw.cert_scrapes`, `raw.e2b_run_logs`, `raw.coin_observations`, `raw.scan_events`.
27. **PCGS public API has a 10k/day quota** (per-token) — `api.pcgs.com/publicapi/coindetail/GetCoinFactsByCertNo` returns HTTP 429 with body `"API calls quota exceeded! maximum admitted 10000 per Day"` once hit. Resets midnight Pacific. Fallback: CFBR + `browser_auth:pcgs.com` cookies (cf_clearance + __cf_bm + cf_chl_rc_ni triplet) bypasses the quota entirely. See Turso policy #755.
28. **PCGS moved off CloudFront** — old `d1htnxwo4o0jhw.cloudfront.net/pcgs/cert/{num}/small` URLs are all 404 across every path variant. New image hosting is `images.pcgs.com/CoinFacts/{design_id}_{spec_id}_SpecSearchHover.jpg` (generic coin-type previews) but actual cert-specific TrueViews load async via JS after page hydration — NOT in SSR HTML even with CFBR + waitForTimeout. Fix path needs XHR interception OR direct PCGS API. See Turso policy #756.
29. **Python urllib default User-Agent gets 403 from R2 public URLs** — `pub-*.r2.dev` returns 403 for `Python-urllib/3.x` but 200 for curl/browsers. Not a permission issue — Cloudflare bot detection on the R2 public endpoint. Fix: set `User-Agent: Mozilla/5.0` header explicitly, OR use curl for probe calls. sigv4 PUT uploads work fine; the quirk is only on GET of the public bucket. See Turso policy #754.
30. **NGC direct fetch needs hyphenated cert_number + `www.` subdomain** — `ngccoin.uk/certlookup/{certnum}/63/` (apex, no hyphen) returns 0 bytes because of a redirect Deno fetch doesn't follow cleanly. Fix: `www.ngccoin.uk/certlookup/{XXXXXXX-NNN}/63/` (www + hyphen-at-position-7 for 10-digit certs). See `functions/scan/index.ts` `fetchNgcDirectly` + commit `fcc9f84`. Pop data still isn't extractable from SSR HTML — it's AngularJS-rendered client-side.
31. **Recursive scraper storms** — parallel calls to scrapers (like `price-guide`) without completion gates or idempotency checks on the calling side (like `consensus-council`) can trigger thousands of runaway Deno processes. Fix: always gate recursion on `newItemsCount > 0` and implement a strict `maxDepth` (typically 1). See commit `storm-fix-20260425`.
32. **Mistral 3-14b Reasoning truncation** — Mistral Reasoning models use massive amounts of tokens for their thought process (~3600 reasoning tokens per 4000 total). Default 4096-token limits will truncate the JSON output. Fix: always set `max_tokens: 8192` or higher in the request body for reasoning models.

---

## Reference docs inside the repo

| Doc | Contents |
|---|---|
| `lkup-plan.json` | Living architecture plan — version bumped every meaningful change |
| `CLAUDE.md` | Claude Code project instructions (React arch, critical rules, consolidation plan) |
| `instructionsforbob.md` | Bob's full operating guide — routes, schema, scan flow, constraints |
| `BOB_CHANNEL.md` | Task queue + session log between Bob and Lovable agents |
| `LOVABLE.md` | Full product spec — pages, design, business rules, data fetching patterns |
| `MONOREPO.md` | Repo structure + ownership model |
| `supabase/reference/SCHEMA_MAP.md` | Full Supabase schema map |
| `supabase/reference/GLOBAL_DATA_MAP.md` | Data model across schemas |
| `supabase/reference/API_PYTHON_MIGRATION_AUDIT_2026-04-08.md` | Audit of api-python → Edge Fn migration |
| `supabase/reference/PARITY_AUDIT_2026-04-08.md` | Python ↔ TS parity audit |
| `GONGBOCOINS_INTEGRATION.md` (in auction_tools) | Gongbo scraper integration docs |
| `~/.claude/projects/-Users-benfife/memory/openclaw_architecture.md` | OpenClaw/BIGMAC agent system docs |

## Reference docs outside the repo (related)

| Doc | Contents |
|---|---|
| `~/.claude/skills/price-coins/SKILL.md` | Canonical pricing workflow (13 sections + 2026-04-08 additions) |
| `~/.claude/skills/audit-parity/SKILL.md` | Python ↔ TS parity audit procedure |
| `~/.claude/skills/lift-module/SKILL.md` | Python → TS porting procedure |
| `~/.claude/skills/fix-stubs/SKILL.md` | Phase 0 stub wiring |
| `~/.claude/skills/plan-validator/SKILL.md` | lkup-plan.json policy validation |
| `~/.claude/skills/lovable-deploy/SKILL.md` | Lovable publish automation |
| `~/.claude/skills/graphify/SKILL.md` | Knowledge graph builder |

---

## Turso fact-logging for cross-agent coordination

After significant actions, write a fact so other agents (Bob, Computer, Main, etc.) stay in sync:

```bash
# Via the helper
facts add operational "description" --tags lkup,session:2026-04-08,agent:claude

# Sync to Turso
bigmac-sync push
```

Tag conventions: `lkup`, `consolidation`, `phase0-5`, `barcode`, `pricing`, `extension`, `desktop`, `enrichment`, `deploy`, `parity`, `architecture`, `agent:bob`, `agent:claude`.

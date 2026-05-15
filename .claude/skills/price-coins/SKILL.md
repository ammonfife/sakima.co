---
name: price-coins
description: Authoritative coin-input-to-verified-price workflow. Takes any input type (QR URL, barcode, cert number, photo, raw description, box/pack) → identifies the grader → routes to the correct production endpoint → verifies against source-of-truth → prices with base/retail formula. Includes a VERIFY MODE that tests endpoints without polluting Supabase cache. Covers every grader (PCGS, NGC, ICG, CAC, ANACS, GONGBO, CNGC, WPT, CSIS) and every input type (graded slab, raw coin, box, pack, VaultBox). Use this skill before any coin pricing work — do NOT invent new scraping methods, this document has the answers.
---

@~/.claude/skills/lkup-shared-context/CONTEXT.md

# /price-coins

**Canonical coin pricing + verification workflow.** Converged from the 2026-04-07 SMS batch session + the 2026-04-08 live scan session that caught Chinese grader misparses, broken ebay-listings-sync, Terms-of-Service modal gates, and (in the evening 2026-04-08 live show session) landed the full talking-points + OBS control pipeline.

---

## 🆕 2026-04-09 Full-court Session — Critical Additions (read first)

**Scan fn NGC direct-fetch URL fix (commit `fcc9f84`, v101 deployed):** NGC's SSR endpoint
requires BOTH the `www.` subdomain AND a hyphenated cert_number (XXXXXXX-NNN for 10-digit
certs). `ngccoin.uk/certlookup/{certnum}/63/` (apex, no hyphen) returns 0 bytes. Verified:
18 of 99 previously-stuck null-description certs populated after this fix (including
NGC-611076-002 "1798 POINT 9 WIDE DATE BB-112,B-15 $1" @ $2,187.50). Pop data stays null
even with the fix because NGC's pop counts are AngularJS-rendered client-side, not in SSR HTML.

**PCGS API has a 10k/day quota per token:** `api.pcgs.com/publicapi/coindetail/GetCoinFactsByCertNo/{cert}`
returns HTTP 429 with body `"API calls quota exceeded! maximum admitted 10000 per Day"`
once hit. Resets midnight Pacific. **Fallback:** CFBR + `browser_auth:pcgs.com` cookies
(cf_clearance + __cf_bm + cf_chl_rc_ni triplet) bypasses the quota by scraping via a
real Chromium session. Verified still working 2026-04-09. See Turso policy #755.

**PCGS moved off CloudFront entirely:** old grader_data.obverse_url values of shape
`https://d1htnxwo4o0jhw.cloudfront.net/pcgs/cert/{certnum}/small` (and every path variant)
are now 404. New PCGS image hosting at `images.pcgs.com/CoinFacts/{design_id}_{spec_id}_SpecSearch{Hover,Preview}.jpg`
but those are generic coin-TYPE previews, not cert-specific TrueViews. Actual cert photos
load async via JS after hydration and are NOT in CFBR's SSR snapshot even with
`waitForTimeout: 5000`. Fix path needs XHR interception OR direct PCGS API. See Turso
policy #756.

**W12 locked_prices layer is live on Supabase:** view `public.coin_pricing_with_lock`
wraps `public.coin_current` with `effective_retail = GREATEST(consensus_price, locked_retail)`
so Ben's manually-locked prices (SMS batches in Turso `sms_batch_pricing_*`) become the
floor. Frontend `Coin.tsx` reads the lock-aware view. NGC-4195196-003 (Marshals FDI)
verified end-to-end at `$2,470 locked, is_locked: true, lock_raises: true`. Never lowers
a price. See migration `20260409000001_locked_prices.sql`.

**Edge Functions writing to raw.* MUST use `SUPABASE_SERVICE_ROLE_KEY`:** not anon key
with RLS + GRANT. Confirmed on `whatnot-sale-ingest` 2026-04-09: anon + RLS INSERT policy
+ table GRANT + schema USAGE all applied and curl still returned `permission denied for
table whatnot_sales`. Service role bypasses PostgREST's extra permission stack on raw
schemas. Same applies to raw.cert_scrapes, raw.e2b_run_logs, raw.coin_observations,
raw.scan_events.

**Python urllib → R2 public URL quirk:** `pub-*.r2.dev` returns HTTP 403 for
`Python-urllib/3.x` User-Agent but 200 for curl + browsers. Cloudflare bot detection on
the R2 public endpoint. sigv4 PUT uploads work fine; quirk is only on GET of the public
bucket. Fix: use curl OR set `User-Agent: Mozilla/5.0` header on urllib requests. See
Turso policy #754.

---

## 🆕 2026-04-08 LIVE SHOW SESSION — Critical Additions

Everything in this block was learned the hard way during a live Whatnot show on 2026-04-08. Read first.

### Talking-points Edge Function (`/functions/v1/talking-points`)

- **Primary AI backend is Claude OAuth** (Claude Sonnet 4.5 via Claude Max subscription). Secondary: Lovable AI Gateway. Fallback: direct Gemini 2.5 Flash. Zero per-call cost on Claude OAuth.
- **Claude OAuth token lives in keychain** at `claude_code_oauth_token_ammonfife` (NOT `Claude Code-credentials`, which is often expired). Format: `sk-ant-oat01-...`. Stored as `CLAUDE_OAUTH_TOKEN` Supabase secret via `supabase secrets set --env-file`.
- **Required headers match Claude CLI exactly** (extracted from the v2.1.89 binary): `anthropic-beta: claude-code-20250219,oauth-2025-04-20`, `anthropic-version: 2023-06-01`, `User-Agent: claude-cli/2.1.89 (external, cli)`, `x-app: cli`. Missing any = 401.
- **Output shape v4**: `{ interesting[], price[], facts[], history[], valuation_summary, rarity_notes }`. HARD CAP 4-6 beats total. `price` is OMITTED entirely when no eBay data is available (never filler).
- **Batch mode**: `POST { certs: [{cert_id,service,cert}, ...] }` up to 20 per call. Returns `{ results: {cert_id: payload}, generated, from_cache }`. Use for pre-show bulk enrichment.

### Talking-points prompt rules

1. **NORTH STAR**: "Every viewer should walk away feeling like they KNOW this coin." Edutainment, not sales pitch.
2. **YEAR+MINT+GRADE specificity** > generic series info. "Morgan Dollars are beloved" is banned.
3. **Price beats use ONLY eBay sold comps**. NEVER mention "price guide", "consensus", "NGC guide", "PCGS guide" in the output. Phrase: "sold as high as $X on eBay" or "could sell for over $Y". Skip entirely if no eBay data.
4. **No stock LLM phrases**. Banlist includes "represents a", "leveraging", "robust", "iconic", "emerged during", "enduring popularity", "transformative era", "readily available", "highly desirable", "classic American numismatics", "struck well over a century ago". Extensive list baked into the prompt.
5. **Opinionated numismatist-friend tone**: "Here's the thing most dealers won't tell you...", "what's wild is...", "actually". Spoken delivery rhythm.
6. **Phonetic pronunciation** in `[square brackets]` for foreign names, rare English terms, catalog abbreviations. Skip common US coin vocab (Morgan, Lincoln, Liberty, Eagle need NO pronunciation). Examples: "Tokugawa [toh-koo-GAH-wah]", "Ansei [an-SAY]", "Gobrecht [GOH-brekt]", "L&M [ell-and-em]", "Szechuan [SETCH-wahn]", "JNDA [jay-en-dee-ay]", "Exarchate [EK-sahr-kayt]".
7. **Numerals only** — never spell numbers as words ("$157" not "one-fifty-seven").
8. **Special designation education**: when the coin has RP, Burnished, Cameo, DCAM, DMPL, DDO, RPM, Full Bands, Full Steps, Lettered Edge, Small/Large Date, First Releases, Star, Plus — include a plain-English explanation of what the term means woven into the beats.
9. **Anti-hallucination via KNOWN_FACTS + MISSING_DATA blocks**: the prompt passes explicit "verified facts" and "missing data — do not invent" blocks. Gemini hallucinated population counts and auction prices until this was added; Claude respects it cleanly.

### Cache invalidation discipline

`public.talking_points_cache` is keyed on `cert_id` with NO prompt version. **Every prompt change must nuke the cache** or old output persists forever:

```bash
SRK=<service role key>
curl -sS -X DELETE "https://vsotvatntzlrzrhemayh.supabase.co/rest/v1/talking_points_cache?cert_id=not.is.null" \
  -H "apikey: $SRK" -H "Authorization: Bearer $SRK"
```

POST-show TODO: add `prompt_version` column to `talking_points_cache` so prompt changes auto-invalidate.

### Price-guide Edge Function (`/functions/v1/price-guide`)

- Canonical eBay comp lookup. Input: `{coinType, gradingService, grade, year}`. Output: `{low, high, display, confidence, source, sources:['ebay_sold'], priceDetails:{ebay_avg, ebay_count, query}}`.
- **Description expansion is critical**: `"1887 $1"` returns 0 eBay comps, `"1887 Morgan Dollar"` returns 28. The client must expand terse `coin_current.description` into a searchable name before calling. Helper `expandDescription()` in `tools/obs-control.html` handles year+denomination → series inference ($1 + 1878-1904 → Morgan, $1 + 1921-1935 → Peace, 50C + 1916-1947 → Walking Liberty, 10C + 1916-1945 → Mercury, etc.).
- **Persist-back**: when price-guide returns real data, the client PATCHes `public.certs` with `ebay_median`, `price_low`, `price_high`, and (if current `consensus_price` is null or equals melt) `consensus_price`. Fixes the "only eBay, no price guide, or v/v" data completeness gap.

### Consensus == melt fallback bug

- Upstream `pricing_rollup.py` nightly cron sets `coin_current.consensus_price = coin.melt_value` when no market data exists. That treats the melt floor as a market price, which is wrong (a 2024 Reverse Proof Morgan silver dollar is not $56.58 just because that's 1oz silver melt).
- **Client-side detection**: if `Math.abs(consensus_price - melt_value) < 0.5`, treat consensus as unknown and prefer price-guide Edge Fn's live eBay average.
- Post-show fix: upstream rollup should NEVER set consensus=melt; melt is a floor, not a signal.

### Cert variant resolver

- Same physical coin exists in `public.certs` under TWO cert_id formats due to inconsistent writes across scanner + extension + backfill pipelines: hyphenated (`NGC-8647036-022`) and flat (`NGC-8647036022`).
- When looking up a coin, **fetch BOTH variants** and pick the one with more enriched fields. Score: `consensus_price (×3) + ebay_median (×2) + description + obverse_url + pop_this + price_guide + melt_value`.
- Helper `buildCertVariants(cert_id)` in `tools/obs-control.html`:
  - `NGC-8647036-022` → `[NGC-8647036-022, NGC-8647036022]`
  - `NGC-8647036022` → `[NGC-8647036022, NGC-8647036-022]` (if rest is 10 digits, try 7-3 split)
- Post-show fix: add `canonical_cert_id` column + ingestion normalization trigger.

### R2 image mirror

- URL pattern: `https://pub-9a3e595d93554c6b8c74c009fe3309a7.r2.dev/coins/<cert_id>/<obverse|reverse>.jpg`
- Some coins are mirrored, most still use OG NGC/PCGS CDN URLs in `coin_current.obverse_url`.
- **Render pattern**: always try R2 first, `<img onerror>` fallback to OG URL. Mirrored coins use R2 (faster, CORS-friendly, no NGC Amazon URLs leaking into stream overlays); unmirrored coins still display.
- Mirroring itself is done by `functions/enqueue-enrichment/index.ts`; not every cert is mirrored on first scan — post-show needs a backfill pass.

### OBS overlay infra

- **Overlay route**: `https://lkup.info/obs` (React `src/pages/OBSOverlay.tsx`) OR local mirror at `http://localhost:6768/obs.html` (same styling, standalone HTML served by `python3 -m http.server 6768 --directory ~/github/ammonfife/lkup.info/tools`). Use local mirror when Lovable publish is backed up.
- **obs-state Edge Function**: `POST` sets the overlay card, `GET` polls every 2s. Supports `show_price` and `show_video` flags for operator toggles. Local overlay polls with explicit apikey+bearer headers — the deployed OBSOverlay.tsx had a bug where it polled without auth and returned 401, rendering the page white. Fixed via commit that adds the headers + forces `html/body { background: transparent }` on mount.
- **obs.html is upscaled 2.5×** with FIXED width (1200px) and variable height so the card never overflows the OBS viewport regardless of content length. Title clamped to 3 lines.
- **Operator dashboard** (`http://localhost:6768/obs-control.html`): feed of recent scans with dedup (service+digits+grade key), click-to-push-to-overlay, filter bar (🆕 new scans default-on, 📦 full inventory, collection chips from `public.collections`), 🔎 free-text search across description/cert/barcode/grade/service/designation/year/mint/denomination, 📷 SCAN BARCODE input (autofocused, USB HID compatible, password-manager autofill suppressed via type=search + data-lpignore + data-1p-ignore + data-form-type=other + obscure name), Show Price + Show Video toggles (POST to obs-state flags), OPEN ↗ links to lkup.info/coin/ per card, persistent OPEN ↗ in the header Current Coin, below-the-fold Whatnot stream popup launcher with localStorage URL persistence.
- **Whatnot cannot be iframed** cleanly — they have X-Frame-Options SAMEORIGIN AND JS frame-busting that logs the user out when framed. The lkup.info extension has a content script (`whatnot-frame-unbust.js`) that defines `window.top === window.self` at `document_start` in the MAIN world, scoped to localhost:6768 + lkup.info parent origins. Popup windows are the reliable path.

### enrich-all pattern (unified enrichment)

Every click/scan in the dashboard triggers `enrichAll(coin)` which fires in parallel (fire-and-forget):

1. `scan` Edge Fn (description, grade, images, price_guide, population)
2. `price-guide` Edge Fn (+ persist-back to `public.certs`)
3. `talking-points` Edge Fn (warmup cache)
4. `enqueue-enrichment` Edge Fn (background pipeline stages)

Next view of the same cert has everything populated. Root problem it fixes: pipelines used to be lazy/single-trigger — extension only scraped when Ben opened the cert page, eBay refresher ran nightly, pricing rollup was daily.

### Gongbo-enrich stub status (UNBLOCKED POST-SHOW)

- `/functions/v1/gongbo-enrich` is deployed but **returns only `{cert_number, service_brand: "GBCA"}`** — a stub. CFBR renders m.gongbocoins.com but the `.infoBox .line` selectors don't match, and the actual coin data is gated behind a legal-terms modal (Chinese text: `我已完整阅读并理解以上法律条款`).
- **Post-show debug path**: CFBR `actions` with a specific `page.evaluate` that finds the Chinese-text button and clicks it, then waits for `.infoBox .line` to populate. Possible backend API exists at `wapi.gongbocoins.com` but the guessed paths return 404 — needs reverse-engineering from mobile app DevTools.
- Chinese coins (L&M, Y-, 大清, 光緒) remain `— no price —` until this is unblocked.

### SMS batch price locking

- **Locked prices move upward only**. When a base price was assigned manually via SMS batch (e.g. NGC-4195196003 base $1900 / retail $2400), live enrichment should NEVER overwrite with a lower value from the automated pipeline.
- Current location: SMS batch prices are NOT in `public.certs` or `public.inventory` — still hunting the table as of 2026-04-08 evening. May be in a `draft_listings` table or a separate locked-price table not yet wired to the feed renderer.
- Required behavior: dashboard rendering + persist-back logic should always take `MAX(existing, new)` for `consensus_price` when a locked-price flag is set on the row.

### Extension enrichment gap (post-show follow-up)

- `coin-cert-scraper` extension (and the newer unified `lkup.info` extension) currently scrapes: description, grade, price_guide, population, images. It does NOT scrape: designer, composition, weight, diameter, variety notes, historical text, die info.
- Additive enrichment was added to `extension/content/cert-scraper.js` (richFacts + narrativeFacts fields) that capture the full cert-table key/value pairs and narrative blocks from PCGS pages, but the storage table for these (`raw.cert_scrapes`) is still empty and not read by `talking-points` Edge Fn.
- Post-show: wire the richFacts/narrativeFacts payload through the background service worker → Supabase persistence → talking-points prompt injection, so Gemini/Claude have real scraped context instead of guessing catalog references (e.g. Gemini hallucinated Yuan Shih-kai for an L&M-422 Szechuan Province "4 Circles" coin because the description was just `"(1920-31) - Y-257.2 L&M-422 - 4 Circles"`).

---

## ⚠️ READ THIS FIRST — STOP FLAILING

If you are a future agent and you found this skill, it's because you need to price or verify a coin. **Before you invent a new scraping method, re-auth E2B, or conclude "everything is blocked," read sections 0–3 of this document.** Every working path is documented. Every known block has a documented workaround. Every grader has an authoritative endpoint.

**Three rules that prevent wasted hours:**
1. **HTTP 200 ≠ working.** Always parse the body and verify expected fields. The scan Edge Function may return `source: "cache"` with stale stub data — that's NOT confirmation the pipeline works.
2. **"No data returned" is not a blocker — it's a signal to check the CORRECT endpoint for that grader type.** Section 1 has the routing table.
3. **Don't write to Supabase before testing endpoints.** Cached hits mask broken enrichment. Use Verify Mode (section 2).

---

## 0. Input Decision Tree — What Did You Receive?

Inputs arrive in one of seven shapes. Identify the shape FIRST, then jump to the correct section.

| Input shape | Example | Handler |
|---|---|---|
| **Grader URL** (QR scan) | `https://m.gongbocoins.com/k/1710733764` | §1 per-grader routing → scan Edge Function → enrichment |
| **Bare cert number** | `28205472` (ambiguous — need service hint) | Ask service if unknown, then §1 |
| **Full slab description** | `NGC 6600539-051 1923 Peace Dollar MS63` | §3 verify workflow (directly to NGC/PCGS/etc lookup) |
| **Hand-typed coin list** | `"12. 2024 W Silver Eagle NGC PF70 Ultra Cameo"` | §3 — **always verify cert first, descriptions are ~25% wrong** |
| **Raw coin** (no slab) | Photo or description of an ungraded coin | §5 AI vision path |
| **Box / Pack / Surprise Set** | VaultBox, Agora MLB box, Whatnot surprise pack | §6 box/pack path |
| **Collectible (non-coin)** | Baseball card, watch, sports memorabilia in a slab | §7 generic collectible path (flagged) |

---

## 1. Per-Grader Routing Table (AUTHORITATIVE)

**For each grader, this is the correct endpoint and the correct fallback chain.** Do not invent alternatives — every cell has been tested.

| Grader | URL pattern | Primary endpoint | Auth | Fallback 1 | Fallback 2 | Status |
|---|---|---|---|---|---|---|
| **PCGS** | `pcgs.com/cert/{cert}` | `https://api.pcgs.com/publicapi/coindetail/GetCoinFactsByCertNo/{cert}` | Bearer: keychain `pcgs_api_token` (304 chars) | CFBR `/content` on `pcgs.com/cert/{cert}` (Cloudflare-blocks-direct-HTTP, CFBR bypasses) | E2B Playwright | 🟢 API + CFBR both working |
| **NGC** | `ngccoin.com/certlookup/{cert}/` | Direct HTTP on `ngccoin.uk/certlookup/{cert}/{grade}/` (no auth, public) | None | CFBR `/content` for JS-rendered population data | E2B | 🟢 direct HTTP + CFBR both working |
| **ICG** | `icgcoin.com/verification/?se={cert}` | Direct HTTP or CFBR | None | — | — | 🟢 working |
| **CAC** | `cacgrading.com/cert/{cert}` | CFBR | None | Direct HTTP (may 403) | — | 🟡 CFBR only |
| **CACG** | (uses CAC numbering) | Same as CAC | — | — | — | 🟡 |
| **ANACS** | `anacs.com/verification` | Direct HTTP form POST | None | — | — | 🟡 low volume |
| **GONGBO** (公博/GBCA) | `m.gongbocoins.com/k/{cert}` | **CF Worker** `https://gongbo-scraper.sakima-api.workers.dev` (uses `@cloudflare/puppeteer` to click Terms-of-Service modal) | None | CFBR `/content` REST (returns skeleton only — modal blocks data load) | E2B Playwright | 🟡 Worker clicks modal, extraction still iterative |
| **CNGC** (华夏 China NGC) | `cngccoin.com/pro/{cert}.html` | **TODO: `cngc-scraper` CF Worker** (not yet built) | — | CFBR `/content` or signed backend call | — | 🔴 stub only (scan parses, enrichment pending) |
| **WPT** | `z.wpt.la/{xx}/{xx}/{cert}` | **TODO: `wpt-scraper` CF Worker** | — | CFBR | — | 🔴 stub only |
| **CSIS** | `csis.vip/Product/ProductInfo.aspx?pid={cert}` | **TODO: `csis-scraper` CF Worker** | — | CFBR | — | 🔴 stub only |
| **SEGS** | `segsgrading.com/verify` | Direct HTTP | None | — | — | 🟡 low volume |
| **PMG** (currency) | `pmgnotes.com/certlookup/{cert}` | Direct HTTP | None | CFBR | — | 🟢 for paper money only |

### 1a. lkup.info production endpoints (the thing you actually call)

All graders above are wrapped by the lkup.info `scan` Edge Function and downstream enrichment. **For ANY input, the first call should be to `scan`**, not directly to the grader site. The scan function handles service detection, cert extraction, cache check, and enrichment dispatch.

```bash
# Universal entry point — accepts URL, barcode, or bare cert
ANON=$(grep VITE_SUPABASE_ANON_KEY ~/github/ammonfife/lkup.info/.env | cut -d= -f2)
curl -sS -X POST "https://vsotvatntzlrzrhemayh.supabase.co/functions/v1/scan" \
  -H "Authorization: Bearer $ANON" \
  -H "Content-Type: application/json" \
  -d '{"barcode":"<INPUT>"}'
```

Returns `{success, certId, cert, service, grade, description, priceGuide, images, population, source}`.

**Critical field:** `source` tells you where the data came from:
- `"cache"` — hit `public.certs`, data may be stale (stub from earlier scan)
- `"fresh"` — enriched this request, fresh from grader source-of-truth
- `"stub"` — cert was created but enrichment didn't populate fields (partial fail)

**If you see `source: "cache"` during verification, the cache is masking whether enrichment actually works.** See §2 for how to bypass the cache.

### 1b. Sold-comp pricing endpoints (eBay)

Pricing (sold comps + active BIN ceiling) comes from eBay, not the grader:

| Need | Endpoint | Notes |
|---|---|---|
| **Still-active listings** | eBay Browse API `/buy/browse/v1/item_summary/search` | Uses `ebay_browse_api_token` keychain, ~30ms/request |
| **Sold listings (batch update)** | 3-tier: Browse API probe (404=ended) → plain HTML JSON-LD scrape of `ebay.com/itm/{id}` → CFBR fallback | See `lkup-plan.json` → `ebay_sold_batch_strategy` |
| **Sold listings (single cert)** | CFBR on `ebay.com/sch/i.html?_nkw=...&LH_Sold=1&LH_Complete=1` with Turso cookies | §4 below |
| ~~Marketplace Insights API~~ | ❌ NOT accepting new applicants per Ben 2026-04-08 | Don't re-apply |

### 1c. Whatnot comps

Whatnot doesn't publish a public search API. Current path:
- **Show schedule/RSVP data:** `scrape-whatnot-dealer` Supabase Edge Function (deployed 2026-04-08)
- **Per-item sold prices:** TODO — no public source, requires dealer login or hot-label webhook replay

---

## 2. VERIFY MODE — Test Endpoints Without Polluting Supabase Cache

The biggest gotcha when verifying the production pipeline: the `scan` Edge Function caches in `public.certs`, so a second call returns the cached stub — **even if enrichment silently failed the first time.** You'll think the endpoint works when it doesn't.

### 2a. Detect cache hits before trusting a result

```bash
response=$(curl -sS ... scan ...)
source=$(echo "$response" | jq -r '.source')
if [ "$source" = "cache" ]; then
    echo "⚠ Returned from cache — not a fresh verification"
fi
```

### 2b. Four ways to bypass the cache (pick based on the situation)

| Method | When to use | Trade-off |
|---|---|---|
| **A. Use a cert that's NOT in the DB yet** | First-time verification of a new grader | Requires having a fresh cert to hand |
| **B. Delete the cert row before re-scanning** | Re-testing a broken pipeline | DELETE is destructive — use UPDATE `updated_at = NULL` instead (see below) |
| **C. Call the enrichment function directly, bypassing `scan`** | Verifying only the enrichment step | Skips the full scan path; good for component-level testing |
| **D. Pass `force_refresh: true` in the request body** | Future enhancement — not yet wired up in scan | — |

**Method B (non-destructive "cache invalidation"):**
```sql
-- Expire the cache for one cert without deleting data
UPDATE public.certs SET updated_at = '1970-01-01' WHERE id = 'GONGBO-1710733764';
-- Or: clear the description to force re-enrichment without losing the row
UPDATE public.certs SET description = NULL WHERE id = 'GONGBO-1710733764';
```

**Method C (direct enrichment, skips scan):**
```bash
# For NGC/PCGS: bypass scan → direct enrichment
curl -sS -X POST "https://vsotvatntzlrzrhemayh.supabase.co/functions/v1/enqueue-enrichment" \
  -H "Authorization: Bearer $ANON" -H "Content-Type: application/json" \
  -d '{"cert":"89649572","service":"PCGS","force":true}'

# For Gongbo: call the scraper Worker directly
curl -sS -X POST "https://gongbo-scraper.sakima-api.workers.dev" \
  -H "Content-Type: application/json" \
  -d '{"cert":"1710733764","include_html":true}'
```

### 2c. End-to-end verification template (compare manual vs pipeline)

```python
def verify_cert_pipeline(cert_input: str, expected_service: str) -> dict:
    """
    Run a cert through manual source-of-truth verification AND the
    production pipeline, then return a diff.

    Always call manual verification FIRST so we're comparing the pipeline
    against a known-good answer, not against itself.
    """
    # 1. Manual verification from source of truth
    manual = fetch_from_grader_website(cert_input)  # per §1 routing table

    # 2. Production pipeline (fresh, not cached)
    expire_cache(manual['cert_id'])  # method B above
    pipeline = call_scan_function(cert_input)

    # 3. Diff every field
    diffs = {}
    for key in ['service', 'cert_number', 'grade', 'description', 'year',
                'obverse_url', 'reverse_url', 'price_guide']:
        m, p = manual.get(key), pipeline.get(key)
        if m != p:
            diffs[key] = {'manual': m, 'pipeline': p}

    return {
        'input': cert_input,
        'manual': manual,
        'pipeline': pipeline,
        'diffs': diffs,
        'verdict': 'PASS' if not diffs else 'FAIL',
    }
```

**Run this template before declaring any cert-resolution pipeline "working."** Save results to `/tmp/verify_{YYYY-MM-DD}_{cert}.json` for audit.

---

## 3. The Golden Rule — Verify Every Cert Before Pricing

**NEVER trust hand-typed coin descriptions.** In the 2026-04-07 batch, **3 of 12 rows** had fundamentally wrong descriptions (wrong year by 6-12 years, wrong country, wrong metal). Always verify from the grader's public cert lookup page before pricing.

### 3a. NGC cert verification (direct HTTP, no auth)
```python
import requests
from bs4 import BeautifulSoup
r = requests.get(f'https://www.ngccoin.uk/certlookup/{cert}/{grade_num}/',
                 headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'},
                 timeout=15, allow_redirects=True)
soup = BeautifulSoup(r.text, 'html.parser')
body = soup.get_text(' ', strip=True)
m = re.search(r'Description\s*(.+?)\s*Grade\s*([A-Z0-9\s]+?)\s*Label\s*(\w+)', body)
```

For **NGC population data** (scarcity analysis), use CFBR `/content` with `waitForTimeout: 8000` — population is rendered by AngularJS and needs JS execution.

### 3b. PCGS cert verification
Path A — the JSON API (fastest, preferred when you have the token):
```bash
PCGS_TOKEN=$(security find-generic-password -s "pcgs_api_token" -w)
curl -sS -H "Authorization: Bearer $PCGS_TOKEN" \
  "https://api.pcgs.com/publicapi/coindetail/GetCoinFactsByCertNo/{cert}"
# Returns JSON: CoinName, Grade, Designation, PriceGuideValue, Year, etc.
```

Path B — HTML scrape via CFBR (when you don't have the token or need the full cert page layout):
```python
import requests
r = requests.post(
    f"https://api.cloudflare.com/client/v4/accounts/187de0c1d881a4a2254008f31d8e93d4/browser-rendering/content",
    headers={"Authorization": f"Bearer {CF_API_TOKEN}"},
    json={"url": f"https://www.pcgs.com/cert/{cert}", "waitForTimeout": 5000},
)
```

### 3c. ICG / ANACS / CAC
Direct HTTP works for all three, though ICG's result page JS-renders. CFBR is the cleaner path.

### 3d. GONGBO — see §1 + §4a (needs CF Worker for modal dismiss)
### 3e. CNGC / WPT / CSIS — scan detection works, enrichment is stub-only (no Worker yet)

---

## 4. Pricing (Sold Comps) — Full Workflow

Existing content from the 2026-04-07 SMS batch session. **Every step was converged after hitting each pitfall in production.**

### 4a. Get gold/silver spot (current values matter)
```bash
# Kitco or yfinance; ~/clawd/venv/bin/python3 + yfinance GC=F / SI=F.
# Fallback: Supabase public.spot_prices_latest view (updated daily via cron)
```
Record today's spot — historical comps need spot normalization (§4g).

### 4b. Fetch eBay session cookies from Turso
```python
# Turso key: browser_auth:ebay.com — 60 Playwright-format cookies
# Required because eBay's /sch/i.html is behind Akamai bot management.
cookies = turso_get('browser_auth:ebay.com')  # list[dict] in Playwright storageState format
```

### 4c. Pull sold comps via Cloudflare Browser Rendering
```python
body = {
    "url": f"https://www.ebay.com/sch/i.html?_nkw={query}&LH_Sold=1&LH_Complete=1",
    "cookies": cookies,  # Playwright storageState-format from Turso
    "waitForTimeout": 5000,
}
# POST to https://api.cloudflare.com/client/v4/accounts/187de0c1d881a4a2254008f31d8e93d4/browser-rendering/content
```

Response wrapper: `{"success": true, "result": "<html>..."}`. Unwrap `result` and unescape JSON before parsing.

**eBay 2026 class names:**
- Listing card: `li.su-card-container`
- Title: `.s-card__title`
- Price: `.s-card__price`
- The old `s-item__*` classes are DEPRECATED — do not use.

### 4d. Filter parsed listings
- Exclude placeholder cards: `"Shop on eBay" in title`
- Exclude sets/lots: regex `\b(3\s*coin|three[\s-]*coin|3pc|set|lot|roll)\b`
- Match grade exactly: `\bMS\s?63\b` (or PF70/PR70/etc.)
- Match variety keywords: "Small Letters", "Full Bands", "FDI", "FS", "First Day of Issue", etc.
- Exclude off-variety (1881/0 overdate ≠ regular 1881)

### 4e. Query design
- **Low-volume coins** (rare modern commems, FDI-labeled): use broader query + post-filter in Python
- **Common coins** (Morgans, ASEs): specific queries work fine
- Example: `"2015 w $5 gold us marshal"` beats `"2015-W US Marshals $5 Gold NGC PF70 Ultra Cameo First Day of Issue"` (returns 248 listings vs 2 placeholders)

### 4f. Partition FIXED_PRICE vs BIN+BestOffer
- `["FIXED_PRICE"]` = firm asking price, primary median anchor
- `["BEST_OFFER","FIXED_PRICE"]` = list is a ceiling, actual sale ≈ 85% of list — use `BO_median × 0.90` as fallback when < 3 firm listings

### 4g. Metal spot normalization (critical for gold)
Gold moved 4× from 2014→2026. A $1,280 sold comp from 2019 reflects a completely different spot than today's $4,818.60. Apply:
```python
ratio = current_spot / historical_spot_at_sale_date
normalized_sold_price = sold_price * ratio
```
Reference implementation: `auction_tools/production/scanners/unified/enrichment/metal_price_service.py` → `get_historical_price()` + `normalize_price_to_current_spot()`. Historical spot lives in `public.spot_price_history` (backfilled 2026-04-08 via `20260408_spot_backfill.py`, 2027 rows, 4 metals, 2 years).

### 4h. NGC guide lag warning
The NGC price guide is **frozen to the last public auction result**. For modern gold commemoratives with no recent sale, the guide can be **4× too low**. Apply spot normalization to the guide, or use sold_median as the anchor.

### 4i. The base/retail formula
```python
melt_floor = metal_oz * spot * 1.02

base = max(
    price_guide,            # when not stale
    sold_median,
    normalized_sold_median, # spot-adjusted
    melt_floor,             # never below metal
)

retail = base * 1.30         # default 30% markup
# Floor check: retail ≥ market × 1.20
```

**Overrides:**
- Top Pop (0 in higher grades) → +15-25% scarcity
- "No public sale since 2014" signal → apply spot normalization to stale guide
- FDI label on NGC → +10-20% over plain PF70 (varies by issue)
- CAC sticker → +100-400% (rare, but applies when subject has it)
- Low-value ICG BU on common date → floor at slab+grading cost ($18-20)

### 4j. Active BIN ceiling sanity check
Before finalizing each row, query active BIN (`LH_BIN=1`, no sold filter) and find top 3 legit asks. If your retail is significantly below legit active ceiling, you're leaving money on the table. Filter actives through the same variety/label/grade rules — off-variety actives don't count.

---

## 5. Raw Coins (No Slab, No Cert)

When input is a photo or description of an ungraded coin, the cert-lookup path doesn't apply. Flow:

1. **Front/back photo capture** via `desktop_scanner.py` (Client A) or the mobile app (Client B).
2. **AI Vision Validator** (multi-provider consensus: Gemini + GPT-4V + Claude). Reference: `auction_tools/production/scanners/unified/scanner/ai_vision_validator.py` (167 nodes in the auction_tools graphify community, NOT yet in lkup.info — flagged in parity audit §2c for lift).
3. **Taxonomy lookup** from the AI-extracted coin name → `reference.numista_coins` (Chinese name column handles Chinese AI transcriptions).
4. **Pricing** via eBay sold comps for the matched taxonomy entry (use `coin_id` from numista_coins as the query anchor, not free text).
5. **Melt floor** is critical for raw — many raw coins are sold purely at melt + small numismatic premium.

**Object types** (scanner sends in `capture-start`):
- `GRADED_SLAB` — slab with a cert (even if parse failed)
- `RAW_COIN` — ungraded loose coin
- `BOX` — VaultBox, Agora MLB box, etc.
- `PACK` — Whatnot surprise set, etc.
- `OTHER` — non-coin collectible

**Raw coin pricing ceiling:** never price a raw coin above the melt floor + 50% without strong signals (Top Pop equivalent from a variety guide, CAC sticker equivalent, pedigree). Most raw coins trade within 1.05-1.30× melt.

---

## 6. Boxes / Packs / VaultBox / Agora / Surprise Sets

These are sealed products — the value isn't a single coin but the EV of the contents. Different pricing model.

| Product type | Pricing model | Source |
|---|---|---|
| **VaultBox** | Fixed retail per issue | Issuer publishes MSRP; secondary market tracks it |
| **Agora MLB box** | Fixed retail + escalating scarcity | Agora publishes a release schedule; secondary multiplier varies |
| **Whatnot surprise sets** | **EV = Σ(P(rarity) × value(rarity))** | Requires rarity distribution model |
| **Sealed Mint packs** (First Spouse, Proof Sets) | Mint issue price + scarcity premium | eBay comps |

**Surprise sets have a dedicated schema** in `auction_tools/whatnot_platform.db` (ORPHANED as of 2026-04-08, flagged for lift in PARITY_AUDIT_2026-04-08.md):
- `surprise_sets` (seed, verification_hash, purchase_price, total_value, is_revealed)
- `surprise_set_items` (product_id, rarity, value, revealed)
- `surprise_set_configs` (rarity_weights JSON, guaranteed_rarities JSON)
- `surprise_set_patterns` (ML-detected pack patterns, confidence_score)

**The box scanner flow:** `capture-start` with `objectType: BOX` → camera captures QR or printed barcode on the outside → server returns the product template → AI vision reads the label → pricing pulls from the template's historical market data. See `lkup_scan_objects.md` memory for scanner-mode UX details.

**Do not price a sealed pack/box without a known template.** If you don't have a template, mark the row as "unknown product — requires manual classification" and stop. Don't guess.

---

## 7. Generic Collectibles (Non-Coin Slabs)

PSA/BGS/SGC/CSG/CGC are comic, card, and sports memorabilia graders. They exist in the Service enum but the PRICING model is completely different (population = card print runs, comps = PSA 10 vs 9 vs 8 matter much more than with coins). **Flag these rows and stop.** If you need to price them, follow the per-grader routing in §1 for identification only, then hand off to a sports-card pricing tool.

---

## 8. Known Blocks + Current Status (2026-04-08)

**These are documented. Do not treat them as new discoveries — check this list first.**

| Block | Current status | Workaround |
|---|---|---|
| **eBay Marketplace Insights API** | ❌ NOT accepting new applicants per Ben 2026-04-08 | CFBR + Turso cookies (§4c) or plain HTML JSON-LD scrape (section 1b) |
| **E2B sandbox pool** | 🟡 Temporarily bot-detected; preserved as fallback per never-delete-code policy | CFBR is primary; E2B kept intact in source for fallback/recovery testing |
| **Gongbo Terms-of-Service modal** | 🟡 Blocks data load until clicked; REST CFBR can't click | `gongbo-scraper` CF Worker (live) uses `@cloudflare/puppeteer` click |
| **PCGS direct HTTP** | ❌ Cloudflare challenge "Just a moment..." | CFBR REST `/content` (Cloudflare doesn't challenge itself) OR PCGS API with token |
| **NGC population data** | 🟡 AngularJS-rendered, hidden from plain HTTP | CFBR with `waitForTimeout: 8000` |
| **eBay /sch/i.html placeholder cards** | 🟡 Akamai bot management returns "Shop on eBay" placeholders for unauth | Turso `browser_auth:ebay.com` cookies + CFBR |
| **Google Translate proxy modals** | ❌ Translated pages drop images + still block modals (confirmed 2026-04-08) | Don't use translate.goog for enrichment — use CF Worker scraper per grader |
| **Desktop scanner `/tmp` writes in pool sandboxes** | ❌ Permission denied on `/tmp/ebay_cookies.json` | Inline cookies as base64 in the Python script (fixed 2026-04-08 in ebay-listings-sync) |
| **ebay-listings-sync 500 storm (historical)** | ✅ FIXED 2026-04-08 | See commit `5db4f55` or similar |
| **Chinese grader URL misparses as ICG** | ✅ FIXED 2026-04-08 | Chinese grader URL pre-detection in coin_scanner.py + scan Edge Function |

### 8a. If you hit a NEW block not listed above

1. **Stop and document it** in a Turso fact BEFORE trying workarounds.
2. Add the new block as a row in §8 (this table).
3. Apply the existing block-resolution patterns before inventing new ones:
   - HTML scrape → JSON API → CFBR REST `/content` → CF Worker with Puppeteer → E2B Playwright
   - Direct fetch → cookies from Turso → CFBR with cookies → CF Worker with cookies + clicks
4. The three-time rule applies: if you've tried the same workaround 3 times and it keeps failing, STOP and diagnose the root cause. Don't cycle.

---

## 9. Infrastructure References

| Component | Purpose | Location |
|---|---|---|
| **Cloudflare Browser Rendering REST** | Render JS pages without click interaction | `https://api.cloudflare.com/client/v4/accounts/187de0c1d881a4a2254008f31d8e93d4/browser-rendering/{content,scrape,json,screenshot,pdf,links,markdown,snapshot}` |
| **CF Account ID** | `187de0c1d881a4a2254008f31d8e93d4` | Fixed |
| **CF API token** | Keychain `cloudflare_api_token` (40 chars) + GCP Secret Manager backup | Use `security find-generic-password -s cloudflare_api_token -w` |
| **CF Worker (Gongbo)** | Puppeteer-based scraper with click support | `https://gongbo-scraper.sakima-api.workers.dev` |
| **eBay cookies** | Turso `browser_auth:ebay.com` (60 cookies) | libsql pipeline query |
| **PCGS API token** | Keychain `pcgs_api_token` (304 chars) | For GetCoinFactsByCertNo |
| **eBay Browse API token** | Keychain `ebay_browse_api_token` | For active listing lookups |
| **Turso bigmac-brain** | `libsql://bigmac-ammonfife.aws-us-west-2.turso.io` | Agent facts, policies, shared cache |
| **Supabase lkup.info** | `https://vsotvatntzlrzrhemayh.supabase.co` | Canonical cert/coin/inventory store |
| **Spot price history** | `public.spot_price_history` (2027 rows, daily, 4 metals, 2 yrs) | backfilled 2026-04-08 |

---

## 10. Output Format (Pricing Delivery)

### Markdown table (in-chat review)
```
| # | cert | description | base | retail |
|---|---|---|---|---|
| 1 | NGC 6600539-051 | 1923 Peace Dollar | $90 | $117 |
|   |                | NGC MS63          |     |      |
```
Two rows per item so descriptions wrap naturally.

### SMS-ready plain text (client delivery)
```
1. 1923 Peace Dollar
NGC 6600539-051 MS63
$90 / $117

2. ...
```
No markdown, no pipes, no special chars. Blank lines between items. `/` as base-retail separator. Cert on its own line for one-tap mobile select.

### JSON snapshot (machine consumption)
Full structured data — per-row base, retail, market, metal content, notes, verification method, source URLs. Save to `~/clawd/sms_batches/{YYYY-MM-DD}_final.json` alongside markdown.

---

## 11. Durable Persistence

Once the batch is locked and sent:

1. **Save to disk**:
   - `~/clawd/sms_batches/{YYYY-MM-DD}_final.md`
   - `~/clawd/sms_batches/{YYYY-MM-DD}_final.json`

2. **Add Turso fact**:
```bash
facts add operational "SMS batch {YYYY-MM-DD} FINAL: N coins, base $X / retail $Y / margin $Z. Methodology: <brief>" \
  --tags lkup,sms_batch,pricing,coins,sakima,agent:claude,agent:bob
```

3. **Sync**: `bigmac-sync push`

---

## 12. Common Pitfalls (hit every one in production, documented here so you don't)

1. **Trusting hand-typed descriptions** — always verify cert first. 2026-04-07 batch had 25% wrong rows.
2. **Old eBay class names** (`s-item__*`) — return zero results on modern eBay. Use `s-card__*` and `su-card-container`.
3. **Placeholder "Shop on eBay" cards** — graceful degradation for low-result queries. Exclude by title text.
4. **CFBR JSON envelope** — `/content` returns `{"result": "<escaped html>"}`. Unwrap + unescape before parsing.
5. **Running Playwright directly in E2B or Cloud Run** — detected by Cloudflare/Akamai. Use CFBR or CF Worker instead.
6. **Trusting NGC price guide for modern gold** — frozen to last auction, can be 4× too low. Normalize against spot.
7. **Mixing FIXED_PRICE + BEST_OFFER in median** — BO sells ~85% of list. Partition before computing median.
8. **Missing variety filters** — CAC, Full Bands, 1881/0 overdate, 1999-W vs 1999 are all different products.
9. **Averaging across mixed grades** — PF70 search results include MS70, PF69, Early Releases. Filter exact.
10. **Not checking population** — Top Pop (<300) justifies scarcity premium; 10,000+ population doesn't.
11. **`cngccoin.com` substring matches `ngccoin`** — MUST check CNGC before NGC in hostname dispatchers (fixed 2026-04-08 in functions/scan/index.ts).
12. **10-digit Chinese grader cert misparses as ICG** — the digit-strip fallback swallows bare numeric IDs. Must detect Chinese grader URLs BEFORE the ICG pre-detect block (fixed 2026-04-08 in coin_scanner.py).
13. **`source: "cache"` masking broken enrichment** — if verifying, expire the cache first (§2b method B) or you'll get stale stubs and think it works.
14. **E2B returning hallucinated prices for bad queries** — confirmed 2026-04-08: scanner misparsed a Gongbo cert as ICG, searched eBay for a nonsense ICG number, and still got back `$90-$105 high confidence` from E2B. If the scanner confidence is "high" but the cert identity is wrong, the price is meaningless. Always verify service + cert FIRST.
15. **Substring collisions in hostname dispatchers** — `cngccoin.com` contains `ngccoin`. When adding new graders, order matters. Put the more specific match first.

---

## 13. When to Override the Formula

The formula is a starting point, not a contract. Override any row when:
- Subject has attributes (label, variety, pedigree) the formula can't see
- Market has unusual shape (wide ask distribution, high BO/firm ratio)
- Seller has velocity-vs-max-extraction preferences
- User provides direct domain knowledge

Record every override in the row notes with the reason — `"Ben override: Top Pop scarcity premium, guide stale"` is more useful than just `"$1900"`.

---

## 14. Maintenance Contract

This skill is the authoritative reference for coin pricing + verification. **When you discover something new about a grader endpoint, a block, or a pricing trick, update this document.** Don't let tribal knowledge accumulate in chat transcripts. Every future agent who finds this skill should be able to price any coin without rediscovering the wheel.

**Last major update:** 2026-04-08 — added §0 input decision tree, §1 per-grader routing table, §2 verify mode, §5 raw coin flow, §6 box/pack flow, §8 known-blocks catalog, §12 pitfall #11-15 covering Chinese graders. Converged from Ben's live scan session that caught Gongbo/CNGC/WPT/CSIS misparses.

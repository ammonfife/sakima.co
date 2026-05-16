---
name: work-on-lkup
description: "Meta-skill for working on lkup.info. Updated 2026-05-16. Extension v1.34.82 + 25+ EFs + 18+ CF Workers. Read NEXT_SESSION.md + docs/integrity/CURRENT_PLAN.md + docs/integrity/WIRING.md before touching anything."
---

# /work-on-lkup

Meta-skill. Read this before doing anything in `~/github/ammonfife/lkup.info`.

---

## 🛑 START HERE — mandatory before touching any code

```bash
cd ~/github/ammonfife/lkup.info
bash scripts/verify-wiring.sh        # actual pipeline state in 30 seconds
```

Then read in this order:
1. **`NEXT_SESSION.md`** — operating rules + current punch list + what was shipped last session
2. **`docs/integrity/CURRENT_PLAN.md` Section 7** — commit drift audit, migration tracker divergence, drift claims
3. **`docs/integrity/WIRING.md`** — full wiring manifest: WIRED / UNWIRED / BROKEN / DEPRECATED for every EF, CF Worker, and table

**Do NOT run `supabase db push`** until the migration tracker divergence in CURRENT_PLAN.md Section 7 is resolved — 30 migration files are untracked and re-applying them would break the DB.

**lkup-plan.json is outdated.** The current authoritative documents are NEXT_SESSION.md and docs/integrity/CURRENT_PLAN.md. The plan JSON exists but has not been maintained since the recovery work began 2026-05-09.

---

## The current working system (updated 2026-05-16)

**Frontend:**
- React 18 + TypeScript + Vite SPA — deployed via **Lovable.dev**. Git push → Lovable auto-fetches → **Publish button required** → `lkup.info` live. Git push alone does NOT deploy.
- iOS app: Capacitor wrapper. Same React codebase.

**Backend — canonical data spine:**
- **Supabase** Pro tier (`vsotvatntzlrzrhemayh`). Three schemas: `reference.*` (third-party data, service_role only), `raw.*` (append-only firehose), `public.*` (canonical, React-readable).
- **Branch: `prod` only.** Never `main`. Never feature branches except for CI-required PRs (merge immediately when green).

**Edge Functions** — two directories, both canonical:
- `functions/` — primary, 25+ functions
- `supabase/functions/` — some duplicated here for Supabase CLI deploy path

Key functions (verified working as of 2026-05-16):
- `scan` — THE canonical barcode entry. Fires 3 enrichment methods in parallel per grader.
- `enqueue-enrichment` — fire-and-forget enrichment. Uses `upsert_pricing_consensus()` RPC.
- `price-guide` — eBay sold comp lookup.
- `pcgs-grade-tower` — fetches price+pop for all 30 Sheldon grades via PCGS API.
- `talking-points` — AI auction pitch.
- `ingest-scope` — writes extension network captures to `raw.network_scope`.
- `backfill-comps` — writes to `reference.market_comps` (2,821 pre-aggregated comp rows).
- `coin-id-hygiene` — runs every 10 min via pg_cron → `coin_id_review_queue`.
- `mirror-image` / `generate-video` / `coin-action` / `learn-selectors` / `listing-draft` / `ebay-publish`

Unwired (exist but have no trigger or broken output — see WIRING.md):
- `parse-page-captures` (no pg_cron trigger), `ebay-sold-webhook` (no caller), `legacy-qr-redirect` (not deployed), `lot-scan` (orphan), `whatnot-sale-ingest` (12 callers, 0 output rows)

**Cloudflare Workers** (18+ workers):
- `e2b-pool-lb` — E2B pool load balancer. **Build failing since 2026-05-09** — fix before next prod push.
- `gongbo-scraper`, `ngc-scraper`, `icg-scraper`, `cac-scraper`, `anacs-scraper`, `segs-scraper` (explicitly skipped at scan:3762 — bug)
- `greysheet-scraper`, `google-shopping-scraper`, `whatnot-comp-scraper`
- `coin-vision` — CF Workers AI vision (writes no DB rows — wiring broken)
- `llava-image-analyzer` — hosts main.js (LLaVA), multitest.js (7-model), **council.js** (pricing council at `/council` — wired 2026-05-16)
- `pcgs-api-proxy` — PCGS API token proxy
- `pcgs-price-scraper` — bulk price scraper via Browser Rendering (`/health` confirmed live, `/fetch-page` not yet fully wired)
- `dealer-scrape-scheduler` (cron → `scrape-whatnot-dealer` EF)
- `spot-price-worker` (cron → `spot_price_history`)

**Deprecated — never use these patterns:**
- **nightly-enrichment CF Worker** — DEPRECATED. No wrangler.toml, never deployed, cron-based enrichment is the rejected pattern.
- **Any pg_cron enrichment** — all enrichment must be trigger-based at scan time or button-initiated.
- **`api-python/` (Cloud Run)** — sunset. Never add code here.
- **Any Google Cloud dependency** — migrating away from GCP entirely.

**New data tables (2026-05-16):**
- `public.marketplace_listing_events` — 103,650 events from 3 merged sources (eBay, Whatnot, legacy comps)
- `public.lkup_attribute_source_map` — 48 designation bridge rows (PL/DMPL/CAM/DCAM/FS/FB/FBL across all graders)
- `public.marketplace_listing_current` — view over events

**Pricing pipeline:**
- `reference.pcgs_price_guide` — 294 rows only (all desig=NULL, pre-migration 30). Fill via lkup_helper "Crawl All PCGS Prices" button in Admin tab. Target ~179K rows from PriceChangesItemsJson.
- `reference.market_comps` — 2,821 pre-aggregated comp rows (coin_type/grade/source/median/count). **Not yet queried by council.js — add this.**
- `public.ebay_listing_xref` — 49,009 sold comps. 43.6% have coin_id. 715 rows have slug-format coin_id (preserved in `coin_id_original` — do not use coin_slug to re-resolve).
- `public.bucket_pricing` — 2,172 rows, 377 with ebay_median (17.4%). `consensus_price` populated on all rows.
- `public.pricing_consensus` — 4,944 rows. `raw_ebay_comps` column = 0 populated (council queries ebay_listing_xref directly — this column is unused).

**Council endpoint (live 2026-05-16):**
- `POST https://llava-image-analyzer.sakima-api.workers.dev/council`
- Queries: ebay_listing_xref, pcgs_top_vams, pcgs_coin_facts, pcgs_price_guide, pcgs_population, feature_multipliers, bucket_pricing, platform_fees
- **Known issue:** returns hallucinated prices when evidence is empty (Llama 3.1 8B on CF Workers AI). Add data sufficiency gate before calling AI.

**Extension:**
- Current version: **v1.34.82** (lkup_helper). MV3, Chrome. Load unpacked from `extension/lkup_helper/`.
- Admin tab has "Crawl All PCGS Prices" button — fires PriceChangesItemsJson paginator across all 9 periods × 2 directions × us+world.
- **grader_data_current view** wired in: scan, price-guide, mirror-image, generate-video. NOT YET wired in: enqueue-enrichment, talking-points, listing-draft, coin-action.

**PCGS data pipeline:**
- `reference.pcgs_coin_facts` — 17,439 rows. 91% have denomination, 93% have year. parent_pcgs_number: 10,798 filled.
- `raw.pcgs_extraction_staging` — 15,940 rows. 325 unpromoted (url_param type not handled by promote function).
- Triggers: `pcgs_extract_on_scope` (fires on raw.network_scope INSERT) + `pcgs_extract_on_capture` (fires on raw.page_captures INSERT).
- PCGS Coin Numbers CSV imported 2026-05-16 — adds pcgs_base_number, full_designation, pcgs_section to pcgs_coin_facts.

---

## When to use which sub-skill

| Task | Skill |
|---|---|
| Price a coin / verify a cert | `/price-coins` |
| Port Python → TypeScript | `/lift-module` |
| Verify ported module | `/audit-parity` |
| Fix broken TODO stubs | `/fix-stubs` |
| Push frontend deploy | `/lovable-deploy` |
| Build knowledge graph | `/graphify` |

---

## HARD DO-NOTs (updated 2026-05-16)

1. **NEVER run `supabase db push`** until migration tracker divergence is resolved (see CURRENT_PLAN.md Section 7 — 30 files untracked).
2. **NEVER disable features to silence errors.** Fix root cause. No --no-verify, no stubs, no disconnecting CI.
3. **NEVER delete without explicit permission.** Migrate, deprecate, rename only. Append-only for raw.* tables.
4. **NEVER write synthetic data to production** to satisfy a screenshot.
5. **NEVER use slug-format values as coin_id** (e.g. `american-silver-eagle`, `morgan-dollar`). coin_id must be pcgs:N, ngc:N, or a proper UUID. Violates Rule 2 in CURRENT_PLAN.md.
6. **NEVER NULL existing data** without first preserving it in a new column (add column, copy, then update). Data is never deleted or zeroed without preservation.
7. **NEVER touch `desktop/unified/interfaces/gui/desktop_scanner.py`** without extreme care — 18k lines, actively co-developed, MUST NOT BREAK.
8. **NEVER add new code to `api-python/`** (Cloud Run, being sunset).
9. **NEVER add Google Cloud dependencies.**
10. **NEVER modify `src/components/ui/*`** (shadcn primitives).
11. **NEVER UPDATE or DELETE rows in `raw.*` tables** (append-only).
12. **NEVER use nightly-enrichment or any cron-based enrichment pattern.** All enrichment = trigger-based or user-initiated.
13. **NEVER call `Sandbox.create()` directly.** Always claim from `e2b-pool-lb.sakima-api.workers.dev/pool/`.
14. **NEVER mark anything completed without verifying actual DB row count or live endpoint response.** HTTP 200 ≠ working. Screenshots only prove UI; always also verify the underlying data.
15. **NEVER use `coin_slug` column as a proxy for `coin_id`** — they are different fields with different meanings.

---

## Critical pitfalls (still valid from prior sessions)

26. **Edge Functions writing to `raw.*` MUST use `SUPABASE_SERVICE_ROLE_KEY`** — NOT anon key. RLS + GRANT INSERT on raw schemas still returns `permission denied`. Service role bypasses PostgREST's permission stack on non-public schemas.
27. **PCGS public API has 10K/day quota** — falls back to CFBR + `browser_auth:pcgs.com` cookies (cf_clearance valid ~257 days from 2026-05-14).
28. **NGC direct fetch needs hyphenated cert + `www.` subdomain** — `ngccoin.uk/certlookup/{XXXXXXX-NNN}/63/` (www + hyphen at position 7 for 10-digit certs). Apex + no hyphen returns 0 bytes.
29. **`reference.*` schema NOT exposed via PostgREST** — only public/raw/graphql_public. Reference tables only via service_role inside EFs.
30. **Lovable deploys are manual** — git push ≠ deploy. Must click Publish OR run `/lovable-deploy`.
31. **Supabase gateway requires auth header even for `no-verify-jwt` functions** — `apikey: <anon>` + `Authorization: Bearer <anon>` required. Without it → 401.
32. **Talking-points cache has no version column** — every prompt change requires manual DELETE from `talking_points_cache`.
33. **Direct `Sandbox.create()` = E2B cost leak** — 2026-04-06 incident cost $1,949. Pool-lb only.
34. **Supabase EF deploys use CLI, not git** — `supabase functions deploy <name> --no-verify-jwt`.
35. **`grader_data_current` view still not wired in enqueue-enrichment, talking-points, listing-draft, coin-action** — those 4 EFs still query raw `grader_data` table directly.
36. **Council.js returns hallucinated prices when evidence is empty** — Llama 3.1 8B makes up numbers. Add data sufficiency gate: if cert_comps=0 AND bucket_comps=0 AND pcgs_guide=0, return `{"error":"insufficient_data"}` instead of calling AI.
37. **`reference.market_comps` (2,821 rows) not queried by council** — pre-aggregated comp data exists but unused. Add it.
38. **PriceChangesItemsJson is paginated** — 500 rows/page, recordsTotal can be 179K+. The crawl button handles this; the CF Worker `/fetch-page` endpoint is not yet wired to an orchestrator.
39. **Python urllib gets 403 from R2 and PCGS API** — Cloudflare bot detection blocks Python user agents. Set `User-Agent: Mozilla/5.0` explicitly.

---

## Key infrastructure

| What | Where |
|---|---|
| Supabase project | `vsotvatntzlrzrhemayh` (Pro tier) |
| Anon key (publishable) | `sb_publishable_zwPWb0Z5XFqw_TsvEosfJw_2aoIjMn4` |
| EF base URL | `https://vsotvatntzlrzrhemayh.supabase.co/functions/v1` |
| Council CF Worker | `https://llava-image-analyzer.sakima-api.workers.dev/council` |
| PCGS price scraper | `https://pcgs-price-scraper.sakima-api.workers.dev/health` |
| Integration gate | `bash scripts/verify-wiring.sh` (Stop hook) |
| Wiring manifest | `docs/integrity/WIRING.md` |
| Drift audit | `docs/integrity/CURRENT_PLAN.md` Section 7 |
| Session handoff | `NEXT_SESSION.md` |
| Turso | `libsql://bigmac-ammonfife.aws-us-west-2.turso.io` |

---

## Deploying changes

```bash
# Edge Function
supabase functions deploy <name> --no-verify-jwt

# CF Worker
cd cloudflare/<worker>
~/.nvm/versions/node/v22.20.0/bin/npx wrangler deploy

# Frontend (via Lovable)
git push origin prod
# Then Publish in Lovable UI OR /lovable-deploy

# Never: supabase db push (migration tracker divergence — see CURRENT_PLAN.md Section 7)
```

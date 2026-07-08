---
name: work-on-lkup
description: "Meta-skill for working on lkup.info. Refreshed 2026-07-08 against LIVE Supabase + repo (not doc counts). UX-first + live-state-first. 53 ACTIVE Edge Functions, extension v1.34.234, public.cert_pricing is the live pricing relation. Do not trust NEXT_SESSION.md or any embedded count as authority; verify live code/Supabase first, then update stale docs."
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

1. **Live code + live Supabase first** — inspect the actual page/function path you are touching and run representative `SELECT *` probes. Do not use doc counts as proof.
2. **`README.md` current-state anchor** — use only when it agrees with live code/schema from this session.
3. **`docs/integrity/CURRENT_PLAN.md` Section 7** — migration tracker divergence and drift claims; verify before acting.
4. **`docs/integrity/WIRING.md`** — wiring manifest; verify exact functions/views/triggers before trusting it.
5. **`docs/integrity/UX_SURFACE_AUDIT_2026-07-07.md`** — useful audit shape, stale where code has changed since.
6. **`NEXT_SESSION.md`** — historical scratchpad only. Must not drive implementation decisions unless revalidated against live code and live Supabase.

**Do NOT run `supabase db push`.** Verified 2026-07-08: `supabase/migrations/` has **771 files on disk vs 687 tracked** in `supabase_migrations.schema_migrations` — an 84-migration divergence (the old "30 untracked" figure is stale). Re-applying would break the DB.

**lkup-plan.json and NEXT_SESSION.md are outdated.** The current authority is: visible UX contract → exact current code path → live Supabase schema/data → then docs. Patch docs only after implementation reality has been verified.

---

## The current working system (verified 2026-07-08 against live Supabase management API + repo)

**Frontend:**
- React 18 + TypeScript + Vite SPA — deployed via **Lovable.dev**. Git push → Lovable auto-fetches → **Publish required** → `lkup.info` live. Git push alone does NOT deploy. `/lovable-deploy` now uses the programmatic API (JWT auto-renew), E2B Playwright only as fallback.
- iOS app: Capacitor wrapper, same React codebase.

**Backend — canonical data spine and read-path rule:**
- **Supabase** Pro tier (`vsotvatntzlrzrhemayh`). Schemas: `reference.*` (third-party, service_role only), `raw.*` (append-only firehose), `public.*` (canonical, React-readable), plus `quarantine.*` and `stg_prod.*` (staging/quarantine surfaces — e.g. `quarantine.certs`, `stg_prod.auction_comps`, `stg_prod.grader_data` — NOT product reads).
- **Canonical backbone:** `public.spine` (exploded backbone authority), `public.coins` (canonical coin layer), `public.certs` (canonical cert layer). All three are BASE TABLES (verified).
- **Verified live relation facts (2026-07-08):** `public.cert_pricing` = BASE TABLE, the live pricing relation. `public.pricing_consensus` does **not exist** as a relation. `public.flat_certs` = VIEW (derived cert-facing read). `public.coin_current` = compatibility VIEW only, not the product contract.
- **No fallback-as-design:** if production writes a field to `spine`/`coins`/`certs`/`cert_pricing`, the user-facing read must come from that source. Derived views are temporary projections only.
- **Current read-path reality (measured):** `src/pages/Coin.tsx` still carries ~46 `flat_certs` references vs 1 `spine` read — the flat_certs fast-path is a migration gap, not success. `Coins.tsx` reads `spine` (4 refs); keep family/breadcrumb UX spine-driven, never rebuilt from tier tables or `coins.series`.
- **Branch: `prod` only.** Never `main`. No feature branches except CI-required PRs (merge immediately when green).

**Edge Functions — verified deployed state (2026-07-08):**
- **53 ACTIVE deployed** (Supabase management API is the truth, not dir counts).
- Source split across TWO dirs — `functions/` (47 dirs) + `supabase/functions/` (49 dirs); drift is known. Deploy via CLI: `supabase functions deploy <name> --no-verify-jwt`.
- Hot paths: `scan` (v490 — canonical `/scan` entry), `enqueue-enrichment` (v178 — fan-out enrichment), `price-guide`, `backfill-comps`.
- Newer (June–July 2026): `stripe-checkout` + `stripe-webhook` (payments), `grade-tower-read`, `marketplace-obs-ingest`, `coin-catalog-enrich`(-ngc), `greysheet/ngc/pcgs-catalog-discovery`, `barcode-detect`, `comps-enrich-ebay`, `comps-rematch`, `greysheet-advanced-repull`.
- For anything beyond these anchors, `docs/integrity/WIRING.md` + `bash scripts/verify-wiring.sh` are the authority — never hardcoded bullets here.

**Execution framing:**
- Start from the visible user experience, not table theory.
- Anchor on actual surfaces: homepage promise, `/scan`, `/coin`, `/coins`, `collections`, `inventory`.
- Never use counts as proof. Use live representative rows, exact page code paths, exact queries, exact trigger/function definitions, exact visible fields.
- Distinguish current state from desired state. A wired compatibility layer is not success if it underserves the UX contract.

**Deprecated — never use these patterns:**
- **nightly-enrichment CF Worker / any pg_cron enrichment** — rejected pattern. All enrichment is trigger-based at scan time or user-initiated.
- **`api-python/` (Cloud Run)** — sunset. Never add code here.
- **Any Google Cloud dependency** — migrating off GCP entirely.

**Current UX-first gaps (verified 2026-07-08; keep rechecking live):**
- `/coin` reads `public.spine` for family/breadcrumb context but slab body fields remain flat_certs-projection-led (46 refs measured). Migration gap toward canonical source reads.
- `/coins` reads `public.spine` for IDs/details; any sibling/family graph rebuilt from tier tables, `coins.series`, or `flat_certs` is a regression risk.
- `collections` / `inventory` must stream repricing from `public.cert_pricing` (verified live); `pricing_consensus` is dead naming — the relation does not exist.
- Collection-trigger enrichment parses canonical `grader:cert[:grade]` ids (fixed 2026-07-07); do not reintroduce legacy `SERVICE-cert` assumptions.

**Extension:**
- `extension/lkup_helper/` — active surface, **v1.34.234** (verified in manifest). Audit as part of end-to-end behavior.

**Verification discipline:**
- When a doc says something is wired, verify the exact page/EF/trigger/query against live code and live relations.
- Prefer `SELECT *` on representative rows and exact function/view definitions over aggregate counts.
- The main question is always: does the user-visible page get the linked cert/coin/sibling/pricing/ownership/breadcrumb data the product promises?

---

## When to use which sub-skill

| Task | Skill |
|---|---|
| Price a coin / verify a cert | `/price-coins` |
| Port Python → TypeScript | `/lift-module` |
| Verify ported module | `/audit-parity` |
| Fix broken TODO stubs | `/fix-stubs` |
| Push frontend deploy | `/lovable-deploy` (API-based; E2B fallback) |
| Build knowledge graph | `/graphify` |

---

## HARD DO-NOTs

1. **NEVER run `supabase db push`** — 771 on-disk vs 687 tracked migrations (84 divergence, verified 2026-07-08).
2. **NEVER disable features to silence errors.** Fix root cause. No --no-verify, no stubs, no disconnecting CI.
3. **NEVER delete without explicit permission.** Migrate, deprecate, rename only. Append-only for raw.* tables.
4. **NEVER write synthetic data to production** to satisfy a screenshot.
5. **NEVER use slug-format values as coin_id** (e.g. `american-silver-eagle`). coin_id must be pcgs:N, ngc:N, or a proper UUID.
6. **NEVER NULL existing data** without preserving it first (add column, copy, then update).
7. **`desktop/unified/interfaces/gui/desktop_scanner.py` is REQUIRED PRODUCTION (~19.8K lines).** Mac dealer-station: USB/BT scanner, multi-cam OpenCV, CTP800BD printer, offline SQLite, cert-scraper bridge `:5556`. NOT fully functional (PR #82: 411 hidden ruff findings). Editing is required: mark `# DEPRECATED <date>: <reason>`, flag `# TODO(unimplemented): ...`, test live hardware after changes. `src/pages/Desktop.tsx` is a thin online-only web client, NOT a replacement.
8. **NEVER add new code to `api-python/`.**
9. **NEVER add Google Cloud dependencies.**
10. **NEVER modify `src/components/ui/*`** (shadcn primitives).
11. **NEVER UPDATE or DELETE rows in `raw.*` tables** (append-only).
12. **NEVER use cron-based enrichment.** Trigger-based or user-initiated only.
13. **NEVER call `Sandbox.create()` directly.** Claim from `e2b-pool-lb.sakima-api.workers.dev/pool/`.
14. **NEVER mark anything completed without verifying actual DB rows or live endpoint response.** HTTP 200 ≠ working. Screenshots prove UI only; also verify underlying data.
15. **NEVER use `coin_slug` as a proxy for `coin_id`** — different fields, different meanings.

---

## Critical pitfalls (renumbered, all re-checked or durable)

26. **EFs writing to `raw.*` MUST use `SUPABASE_SERVICE_ROLE_KEY`** — anon + RLS/GRANT still returns `permission denied` on non-public schemas.
27. **PCGS public API: 10K/day quota** — falls back to CFBR + `browser_auth:pcgs.com` cookies.
28. **NGC direct fetch needs hyphenated cert + `www.` subdomain** — apex + no hyphen returns 0 bytes.
29. **`reference.*` NOT exposed via PostgREST** — service_role inside EFs only.
30. **Lovable deploys are manual** — git push ≠ deploy. `/lovable-deploy` uses the programmatic API (JWT auto-renews); verify via `/build-info` SHA.
31. **Supabase gateway requires auth header even for `no-verify-jwt` functions** — `apikey` + `Authorization: Bearer <anon>` or 401.
32. **Talking-points cache has no version column** — prompt changes require manual DELETE from `talking_points_cache`.
33. **Direct `Sandbox.create()` = E2B cost leak** ($1,949 incident 2026-04-06). Pool-lb only.
34. **EF deploys use CLI, not git** — `supabase functions deploy <name> --no-verify-jwt`.
35. **`/coin` and `/coins` are not fully spine-native** — Coin.tsx still ~46 flat_certs refs (measured 2026-07-08). Audit visible sections against `public.spine`.
36. **`pricing_consensus` is dead naming — the relation does not exist** (verified 2026-07-08). Use `public.cert_pricing`.
37. **`public.coin_current` is a compatibility VIEW only** — not the product contract.
38. **PriceChangesItemsJson is paginated** — 500 rows/page, recordsTotal 179K+; CF Worker `/fetch-page` not yet orchestrated.
39. **Python urllib gets 403 from R2/PCGS** — Cloudflare bot detection; set `User-Agent: Mozilla/5.0`.
40. **This skill exists in TWO places** — `~/.claude/skills/work-on-lkup/` AND `~/.openclaw/skills/work-on-lkup/`. Update BOTH or they drift (they did: disk held the 2026-05-16 version while a 2026-07-08 draft circulated unwritten).

---

## Key infrastructure

| What | Where |
|---|---|
| Supabase project | `vsotvatntzlrzrhemayh` (Pro tier) |
| EF base URL | `https://vsotvatntzlrzrhemayh.supabase.co/functions/v1` |
| Deployed EF truth | `supabase functions list` / management API (53 ACTIVE as of 2026-07-08) |
| Council CF Worker | `https://llava-image-analyzer.sakima-api.workers.dev/council` |
| PCGS price scraper | `https://pcgs-price-scraper.sakima-api.workers.dev/health` |
| Integration gate | `bash scripts/verify-wiring.sh` (Stop hook) |
| Wiring manifest | `docs/integrity/WIRING.md` |
| Drift audit | `docs/integrity/CURRENT_PLAN.md` Section 7 |
| Owner handoff | `PM_PROJECT_OWNER_STATE_2026-07-07.md` |
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
# Then /lovable-deploy (programmatic API) OR Publish in Lovable UI

# Never: supabase db push (771 on-disk vs 687 tracked migrations)
```

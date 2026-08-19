# What actually got built in lkup.info, Aug 9 → Aug 15

All measurements as-of **2026-08-15 ~18:35 MDT**. Where I quote a number I measured it — live DB, live API, or the repo — not a commit message. Retractions are at the bottom, including one of my own from this session.

**Scale first, because it changes how you read everything else:** 932 commits, of which **653 are automated** (auto-sync, pre-push hook, Lovable bot). A subject-line skim would have shown you 279 commits and missed most of the week — the automated ones carry the 814k-row facet corpus, the session logs, and the schema dictionary regeneration. Census was by lines-per-file, not by message.

Authors: Ben Fife 359 · auto-sync 312 · pre-push hook 222 · gpt-engineer-app (Lovable) 37 · Claude 2.

---

## The five things that actually happened

### 1. The comp matcher got fast, then got proven pointless-until-the-data-lands

This is the most important intellectual result of the week and it's a *negative* one, which is why it's worth reading carefully.

Aug 9–11 was a matcher performance campaign. Measured start: `lkup_match_comp` was **2.5–9.2s per comp** on real titles (worst case 9.20s on "2022 1c Lincoln Shield Cent PCGS MS65RD", 2,657 candidates). At ~700 observation rows per scan that's 30–107 minutes of matcher work per scan against a 15s drain budget. Fixes shipped: covering index on the spine year gate (145x), first-ever `VACUUM` on `spine` and the two matcher tables, and a boolean-facet-matrix / n-gram / BitmapAnd shape that got it to **<100ms per comp** and made it scale with comp length instead of candidate count.

Then it was tested against 24 real titles and **failed 21 of them** with zero survivors. The root cause chase ended somewhere different from where it started:

- `reference.lkup_attribute_value_alias` covers **93 of 7,306** distinct normalised values in spine's low-cardinality columns — **1.3% coverage**.
- The `*_canonical` columns are not canonical: `mint_canonical` holds **9,220 distinct values** where the real vocabulary is ~34 mints; `series_canonical` holds **341,297** where it should be ~331; `variation_canonical` is populated on **0 rows**; `strike_canonical` on 743 of 814,006 (0.09%).

Conclusion recorded in `audit/artifacts/matcher-perf-findings-20260811.md`: the architecture is correct and fast, but "it has almost nothing correct to intersect ON. This is a data/build problem, not an algorithm problem." Wiring the matcher against 1.3% alias coverage would measure nothing.

**Where that leaves you:** comps sit at **39,975 matched of 97,420 (41%)**. The named highest-value build item is a live refresh of the alias table off live spine (~7,300 values, not 1,041 rows), then rebuilding the canonical arrays through it. That has not been done.

### 2. Spine identity surgery — real merges, real repairs, and one lane now gated shut

Aug 12–13 was hands-on identity work, and it's genuine: 1881-S Morgan exact siblings merged; 1986 / 2010 silver-vs-gold Eagles split; a 2020 emergency Eagle split off a 1943 cent; 24 NGC certs merged onto verified PCGS siblings via `pcgs_number`; 8 PCGS onto NGC via `ngc_id`; 8 CACG onto verified siblings; 160 ICG identity-empty stubs quarantined; **5,184 comps re-pointed** after the merges. Spine is now 814,707 rows.

The headline commit was "fix silent zero-identity onboarding for every new NGC/PCGS scan." I checked it, and the check is the reason this section reads the way it does.

Certs created since that commit (Aug 13 22:01Z): **116, of which 53 have NULL `coin_lkup_uuid`**. Before it: 199, of which 2. That looks like a catastrophic regression until you cut it by service:

| service | new certs | null identity | of those, has a description |
|---|---|---|---|
| PCGS | 20 | 2 | 1 |
| NGC | 59 | 17 | 1 (16 are un-enriched stubs, no description) |
| **ICG** | **28** | **28** | **27** |
| ANACS | 3 | 3 | 3 |
| CAC / SEGS / WPT | 6 | 3 | 3 |

The primary lane is healthy — PCGS 90% identified, NGC 71%. The nulls are **minor graders, and they are scraping fine**: ICG certs come back with a full description and then get no identity at all. That is the deliberate gating from "quarantine ANACS parser risk and gate member IDs." It is NULL-over-bad behaving correctly, and it is also a lane that is currently 0% productive. See finding #1 in the open-items list below — the replacement for it was built and never applied.

### 3. Scan got measurably faster, and the proof was taken against live production

The best-evidenced work of the week. Someone benchmarked against **live lkup.info/scan** rather than a local build, and found that with `BarcodeDetector` unavailable — i.e. Safari and iOS, i.e. every dealer on a phone — the **first decode took 3,435ms while every subsequent decode took ~21ms**. That's not decode time, it's the worker booting and pulling a 238KB zbar wasm at the exact moment someone is holding a slab to the lens. Chrome hid it entirely because its native detector answers first.

Fix: build the worker and push a 1x1 frame through it the moment the camera goes live. Live-prod re-measurement: **first decode 3,435ms → 416ms**. Alongside it: `getUserMedia` calls 6 → 2, scan-loop fork ratio 3.72 → 1.17, cadence capped, camera restart storm killed.

**I verified this is deployed right now**, not just committed — pulled the live index bundle, followed it to the lazy `CameraInput` chunk, and found the `lkupScanStats` marker present. Evidence lives in `audit/perf/live/zbar.log` and `zbar-after-prewarm.log`.

### 4. Cert readiness → auto-print, built by brute-force iteration

Aug 13–14 produced a cert-readiness state machine wired into the realtime lifecycle, driving auto-print gating, comp-invalidation epochs, and print dedup. Manual and automatic print semantics were separated; auto-print now queues until readiness rather than firing on a startup race.

It was built by iteration rather than design: **29 distinct migration files named `wire_cert_readiness_realtime.sql`** and **26 named `grader_evidence_gate_and_truthful_onboard.sql`**, all with different timestamps. I checksummed the 29 — all 29 contents are different, so this is genuine successive refinement, not a stuck loop. But it means the repo now has 220 distinct migration versions in a 6-day window covering maybe 40 logical changes, and several of the intermediate filenames are dead weight (there are matching "Remove duplicate readiness migration filename" commits, so this was noticed).

Related and genuinely good: a **grader evidence admission gate**. Certs no longer get minted before positive page evidence exists; `enqueue-enrichment` stopped first-minting certs; all-zero cert numbers are now forbidden at the DB and rejected in the shared parser; grader pages stay retryable until verified.

### 5. Legal, licensing and marketing exposure got closed — and I verified it against the live anon key

Two passes (Aug 9 and Aug 15) stripped every named competitor and the replacement claims behind them from public marketing, corrected "Order Management is CSV import, not live Whatnot sync," and removed voluntary promises from ToS/Privacy while fixing consent persistence.

The substantive one is the licensed-pricing lockdown. Before it, with the *published* anon key, anyone could read Greysheet `cpg_val`/`grey_val` — and `POST rpc/insert_greysheet_prices` returned **204, an anonymous write into a licensed table**.

I re-ran those probes live just now:

| surface (anon key) | before | now |
|---|---|---|
| `reference.greysheet_prices?select=cpg_val` | 200 | **401** |
| `rpc/insert_greysheet_prices` | 204 (write!) | **401** |
| `rpc/project_guide_tower` | 200 | **404** |
| `mv_cert_pricing_evidence` | 200 | **401** |
| `reference.grade_shape` WRITE | 200 | **401** |
| `greysheet_prices?select=gsid,coin_name` (must keep working) | 200 | **200** |
| `flat_certs` (must keep working) | 200 | **200** |

Closed correctly, with the product left intact. The instrument chosen was a column-scoped `GRANT` rather than dropping the RLS policy — dropping it would have denied every row to anon and broken `/coins`.

---

## What's built but not live — the actionable list

### 1. The minor-grader identity fix is in the repo and not on production

`supabase/migrations/20260812194500_source_qualified_minor_grader_synthetics.sql` replaces the bare `synth:<hash>` member key with a source-qualified `<service>:synth_<hash>`. It has **no applied version on prod**, and I confirmed by live introspection rather than by the migration ledger: `pg_get_functiondef('public.onboard_minor_grader')` on production still contains the **bare `synth:` shape**, and contains no `synth_` form.

Live consequence: `public.coins` holds **101 bare-synth coins and 0 source-qualified ones**, and the **last bare-synth coin was created 2026-08-13 09:23Z**. No synthetic minor-grader member has been minted since. That is the same 28-of-28 ICG / 3-of-3 ANACS zero-identity population from section 2 — the old path was gated off, and its replacement never shipped. This is the single highest-value thing to land.

### 2. 36 window migrations exist in the repo with no applied version on prod

Local versions dated ≥ 20260809: **220**. Applied on prod in that range: **185**. Overall the repo holds **1,363 migration versions against 1,145 recorded remotely — 218 local-only.**

Some of the 36 are duplicate filenames of changes applied under a different timestamp, so don't read it as 36 unapplied changes. But these five are worth an individual decision:

- `20260812194500_source_qualified_minor_grader_synthetics.sql` (finding #1)
- `20260815034500_lock_down_licensed_pricing_anon_p0_p3.sql` — *this one is fine*: applied directly, verified live above; it just has no ledger row
- `20260815012000_certs_fill_raw_barcode_reject_placeholders.sql`
- `20260814053000_disable_marketplace_observations_rls.sql`
- `20260813120000_deprecate_register_coin_from_grader.sql`

The working pattern here is apply-direct-then-backfill-the-file (there's an explicit "recover 22 direct-to-Supabase migrations missing from repo" commit on Aug 13), so absence from `schema_migrations` proves nothing on its own — each one needs the live-object check I did for #1.

### 3. Licensed Greysheet values are still readable by anonymous users on `/coin`

Live, right now, with the published anon key:

```
GET flat_certs?select=cert_id,cdn_bid,cdn_ask
→ [{"cert_id":"anacs:00018797","cdn_bid":8800.00,"cdn_ask":11000.00}]
```

This is documented as a **deliberate exclusion** — a column-level REVOKE makes PostgREST 403 the *entire* request, which would blank `/coin` for every anonymous visitor, because `cdn_bid`/`cdn_ask` are named in `FLAT_CERTS_FAST_COLUMNS` (`src/pages/Cert.tsx:165`) and in `cert-display-source.ts:206`. It needs a frontend column-list split first, plus a decision: admins authenticate as PostgREST's `authenticated` role, so there's no way to withhold licensed columns from free signups without an admin-gated SECURITY DEFINER RPC. Given the rest of the licensing pass got closed, this is the remaining hole.

### 4. Page audit leftovers

The Aug 14 authenticated sweep covered all **72 routes: 63 PASS, 5 EMPTY_BODY, 4 SUSPECT**. Empty: `/camera`, `/obs`, `/obs/:obsKey`, `/obs_qr`, `/obs_qr/:obsKey`. Suspect: `/oldhome`, `/dealer/:slug`, `/terms`, `/terms-of-service`. Aug 15 commits address the `/obs` keyless case and the terms pages, so that artifact predates its own fixes — worth re-running rather than reading.

### 5. `BackfillAdmin.tsx:125` selects a column that doesn't exist

Found in passing during the licensing work: it selects `coin_id` on `reference.greysheet_prices`, which has no such column (real one is `coin_ref_id`). That page has been returning HTTP 400 (42703) all along. Pre-existing, unrelated to the lockdown, still broken.

---

## Also shipped, in less depth

- **Browser extension: 1.34.291 → 1.39.0, 27 releases.** Auto-capture gated behind a target allowlist (it was scoping every page); `network_scope` 403 loop fixed (control signals were being written as data); a failed price lookup no longer renders "ANALYZING" forever; the badge stopped covering eBay's watchlist heart; `coins.mint` holds *names*, so `mint=eq.S` matched nothing and the bucket lane was dead for every US mintmarked coin. Then the Whatnot show tooling: snap panel with lookback frame buffer, burst mode, pointer-capture drag, copy-for-chat line, and a deliberate launch dock (v1.35.0) for the Whatnot panels and OBS overlay. One clean revert on the way (v1.34.301 backed out a candidate-UUID change that broke every lookup).
- **NGC price-guide repair (#11883).** The asterisk flag is now persisted instead of baking a ×1.25 into the price; an in-place repair migration undoes the existing inflation, with a double-apply guard added after Ben flagged it. Low-end band grades are no longer discarded, and circulated slabs stopped being mislabeled MS.
- **DB hygiene that had never been done.** `ANALYZE` across the whole database — **400 of 419 relations had never been analyzed**. `public.comps` reported `n_live_tup` 2,054 against `reltuples` 85,287, a 41x error, while carrying 9 triggers including the matcher — so the planner was choosing matcher plans off garbage stats. Four matviews were 72–81h stale. First-ever vacuum on spine and the matcher tables.
- **Supabase EF auto-deploy unbroken.** An un-clonable filename had been killing every run. Verified: ~50 Edge Functions share a single `updated_at` of **2026-08-15 01:49:56**, i.e. one mass redeploy the moment the fix landed. New EF `route-event` created Aug 12 (restricted data route event capture).
- **Desktop scanner.** NDI phone cameras (native receiving, saved-camera restore, explicit start/stop per slot, previews fill their slots), desktop scans unified through the Supabase pipeline, auto-print gated on canonical cert readiness.
- **Splash / recent-scans.** A personal recent-scan rail on the splash, backed by authenticated history when signed in and localStorage when not, promoted to shared browser session state, surfaced on the dashboard and in OBS control; batch mode honored across all splash scan paths; race-safe collection appends.
- **Owner-scoping** applied to `/orders`, `/analytics`, `/listings`, `/listings/:id`, `/dashboard`, `/crm`, `/inventory`.
- **Real `?q=` coin search**, and cert numbers stopped being written into `raw_barcode`.
- **Council**: sparse coins emit anyway, thin bundles may `web_search`, brace-safe JSON parse, guards hold verdicts instead of discarding them.

---

## Documentation that has gone stale

Three places where what's written down no longer matches the system:

1. **`CLAUDE.md` says `audit/LOOP_LEDGER.md` is "the SOLE live source of truth."** It was last modified **Jul 26** — untouched through this entire window. The artifact actually being maintained is the `audit/deployed-state*.html` report and its CHANGE LEDGER. Anyone booting on the ledger will be reading a three-week-old picture of a system that moved a lot.
2. **`CLAUDE.md` says `core.hooksPath` is the default `.git/hooks` and the in-repo `.githooks/*` is NOT active.** It is now set to `.githooks`, and the pre-push hook runs 5 blocking gates including the migration tripwire. That line is inverted.
3. **The licensed-pricing migration header claims "all ten of those surfaces now 401."** `GET reference.grade_shape` returns **200** — the DDL only revoked INSERT/UPDATE/DELETE/TRUNCATE on it, never SELECT. Reads may well be intended to stay open, but the header says otherwise, and it's the kind of self-describing claim that gets quoted later.

---

## Retracted this session

- **I said the zero-identity onboarding fix was working cleanly** — cut at "since Aug 14 12:00" I got 0 of 26 certs with null identity. That window was a tail slice. Widened to the actual commit boundary it's **53 of 116**, and cut by service it's a minor-grader story, not a fix story. The narrow cut looked right because PCGS/NGC volume dominates the tail. Corrected in section 2.
- **I suspected the 29 identically-named readiness migrations were an agent stuck in a loop.** Checksummed all 29: every one is distinct content. Genuine iteration, retracted.
- **I nearly reported the migration gate as resolved.** `check-migration-gate.sh` prints "✓ migration gate: 1363 local versions (delta 0)" — but reading the script, delta is movement *since the last push*, not local-vs-remote drift. The gate is a tripwire on large swings, not a measure of reconciliation. The real drift is the **218 local-only versions** measured directly against `supabase_migrations.schema_migrations`, and the Supabase prod-branch check remains held shut by a failing status. That hazard is unchanged.

## Unverified

- Whether extension v1.39.0 is actually loaded in the browsers that matter — the manifest says 1.39.0 in-repo; I did not check a running browser.
- Whether the 36 local-only migrations beyond `onboard_minor_grader` were applied directly under other version stamps. Settled per-migration by checking the live object it defines, same method as finding #1.
- Whether the un-analyzed-relations / vacuum work produced a measurable end-to-end scan improvement. The individual gate went 145x faster; nobody re-measured a whole scan afterwards.

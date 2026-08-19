# What actually got built in lkup.info, Aug 9 → Aug 15

813 commits on `prod` since Aug 9. 530 of those are `auto: sync` / knowledge-snapshot noise from the hooks — the real number is **283**, and they cluster hard: 25 / 32 / 37 / 34 / **131** / 24 across Aug 10–15. Aug 14 was a marathon.

Six things actually got built. One of them was an outage that had been silently running for seven weeks.

---

## 1. The EF auto-deploy lane had been dead for 7 weeks — root cause found and fixed

This is the biggest single finding of the week and it isn't a feature.

On 2026-06-24, commit `52166d50c` committed a file whose *filename* was captured terminal output — it contained a literal newline and a `✻` glyph. CLI git tolerates control characters in a path. The Supabase GitHub integration does not; it clones with a strict go-git-style client that validates every path and **refuses the entire repo**:

```
failed to clone repo: invalid path "…-c.txt\n\n✻": contains control character
```

That was the complete "Supabase Preview" check output on *every* prod commit from 2026-06-24 to 2026-08-15. The integration never reached the repo contents, so `supabase/functions/` was never read and nothing auto-deployed for ~7 weeks. Every EF deploy in that window was `scripts/deploy-ef.sh` run by hand — which is exactly why the tree looked healthy while the lane was dead. One byte in one filename, and the failure lived in a check-run summary nobody read.

Fixed Aug 15 (`fix(deploy): unbreak Supabase EF auto-deploy`), plus a blocking pre-push gate: `scripts/check-invalid-paths.sh`.

Worth correcting your mental model: the note that EF auto-deploy was "restored 2026-08-05 by killing the symlink farm" was wrong. The symlink farm was *a* problem; the control character was *the* problem, and it survived that fix by ten days.

Current EF deploy drift is now measured, not assumed — `audit/artifacts/ef-deploy-status-20260814.tsv` has per-function version/lag. Most functions are at lag 0; `ebay-sold-webhook` (lag 10), `legacy-qr-redirect` (9), `listing-draft` (8) and `barcode-detect` (4) are the stragglers.

---

## 2. Spine / facet identity convergence — the largest body of work

Roughly 90 migrations across Aug 11–13, and it's the most consequential engineering of the week. Three phases:

**Phase A — the matcher was 30–90× slower than anyone believed.** `lkup_match_comp` was measured at **2.5–9.2 seconds per comp**, not the 80–100ms in the brief (that number belonged to `lkup_resolve_comp_v2`, a different function). Root cause: the year gate heap-scanned `spine` to evaluate its own WHERE clause, and `public.spine` (813K rows, 1GB) **had never been vacuumed**. Fix was a covering index plus the first-ever VACUUM ANALYZE on spine and five other never-analyzed matcher relations. Measured: gate buffers 9,883 → 139, the gated CTE 3,130ms → 21.6ms per call, the full function 1,913–9,554ms → **64–123ms**. `/coin` keyed read did not regress (0.67–2.04s → 0.57–0.77s). Full writeup with before/after EXPLAIN in `audit/artifacts/matcher-perf-findings-20260811.md`.

**Phase B — the "just backfill spine columns" plan was killed after a production dry run.** `audit/spine-facet-convergence-plan-20260812.md` is the plan of record. The proposed `build_spine_row` patch could copy identifiers within existing UUID groups but could not *establish* missing cross-grader groups, mapped CAC/CACG to `cac_id` instead of `gsid`, and silently picked a winner when a grader had several IDs. The decisive counterexample: SEGS 500072 has one source row, no shared catalog identifiers, and no `coin_decode_explode` row — no `MAX()` over the current group can invent it. So it became an acquire-and-decode problem, not a backfill.

Along the way it surfaced that there are **no correctly source-keyed ICG, GONGBO, CNGC, CSIS or WPT members in `public.coins` at all** — 186 legacy rows all labelled `grader = 'synth'` with no parent identity. Their zero-valued spine columns are an acquisition gap, not a projection gap.

**Phase C — actual data repair, Aug 13.** Crosswalk merges executed with per-batch migrations and a revert migration when a batch proved false (`revert_anacs_pcgs_false_crosswalk_merges`): 24 NGC certs merged onto verified PCGS spine siblings via `pcgs_number`, 8 PCGS onto NGC via `ngc_id`, 8 CACG onto NGC/PCGS, plus catalog-wide NGC↔PCGS and CACG batches. 160 ICG identity-empty stub certs quarantined. **5,184 comps re-pointed** after the merges orphaned them. A dozen individual mis-linked coins split apart by hand (1992 gold Olympics from silver eagle, 2020 emergency eagle from 1943 steel cent, 2013 Maple Leaf from 1998 gold eagle, Franklin halves, and so on). Also: `lkup_canonical_breadcrumb` and `lkup_canonical_uuid` were formally banned in the DB, and `register_coin_from_grader` was documented dead-for-identity.

**The asset nobody is reading.** `audit/artifacts/coin_facet_tokens.tsv` is 813,957 rows, exactly 1:1 with `public.spine`, ~23 facet keys, `\x01`-delimited. There is **no DB object holding it** — no table, no view, no function references it. Companions: `ground_truth_comps.tsv` (1,207 barcode-verified labelled comps — the only sound label source in the system) and `facet-match-scorecard.tsv` (a prototype matcher already scored against that ground truth, +4,454 / −3,246). Built by agents Aug 10–14 and auto-committed. Your instruction on Aug 15 was that this should be remembered rather than abandoned; as of now it is a file on disk and nothing more.

---

## 3. `/coin` became `/cert`, and the whole dealer console went admin-only

`src/pages/Cert.tsx` is new — 5,173 lines. `/coin` and `/coin/:certId` now route to `LegacyCoinRedirect`. This is the single biggest user-visible change of the week and every label QR, OBS overlay line and external link now points at `/cert`.

Simultaneously, `/orders /analytics /listings /listings/:id /dashboard /crm /inventory /sold /scout /labels /desktop /build-info /vendor/:id/financials` all moved from `ProtectedRoute` (any logged-in user) to `RequireAdmin`. `/search` now redirects to `/`, `/oldhome` redirects to `/home`, `/scan-v2` and `/scan-test` are admin-gated. New `/data/*` route for restricted-data route-event capture.

A full 72-route page audit ran on Aug 14 with chromeless-aware verdicts and a PHASE 8 scorecard.

---

## 4. Legal exposure assessment, then code changes to close the gaps

`audit/legal/LITIGATION_EXPOSURE_2026-08-14.md` (28KB) scored ten risks on severity × likelihood. The framing is the useful part: **the exposure is not in the documents, it is in the gap between what the documents promise and what the code does** — which is the worst shape of risk, because your own 637-line ToS becomes the plaintiff's Exhibit A.

Two RED findings, both small code changes:

- **R1 (score 20)** — `src/lib/pricing-access.ts` returned `showGreysheetPricing: true` for *any* authenticated non-admin. So a free account saw `cdn_bid` and `cdn_ask` — CDN's flagship licensed product — while ToS §8A.8(a) promises it's shown only to entitled users.
- **R2 (score 16)** — NGC + PCGS Price Guides reproduced as a full 36-grade table on public pages.

Both were fixed Aug 15 (`fix(legal): entitlement-gate Greysheet, cite melt spot source, attest before eBay publish`, plus migration `lock_down_licensed_pricing_anon_p0_p3`). Also shipped: ToS/Privacy stripped of voluntary promises the code doesn't keep, consent persistence fixed, and marketing copy on `/dealer` brought into line with `/home` — same features, same "On roadmap" tags, because a dealer with both tabs open could see the contradiction and a pre-order sold as shipped is plain false advertising.

Still open in that file: R3 (grader photos re-hosted on your R2 CDN), R4 (AI talking points → one-click eBay publish), R5 (acquisition authorization basis for `source: ngc_ccgops`), R6 (no tech E&O / cyber insurance confirmed).

---

## 5. Whatnot / live-show tooling — extension went 1.34.292 → 1.39.0

Twenty-plus releases in six days. The substantive ones:

- **v1.35.0 launch dock** — deliberate on-demand injection for Whatnot panels and the OBS overlay, replacing content-script matches that never fired on the SPA.
- **Snap panel**, rebuilt across four releases: lookback frame buffer, burst mode, pointer-capture dragging, price refresh, capture history, seen-on-Whatnot marking, deep links, NGC grade segment parsing, and hydration from `flat_certs`.
- **New content scripts**: `whatnot-launcher.js`, `ebay-price-fastlane.js`, `price-lookup-deadline-guard.js`, `grader-evidence-observer.js`, `grader-admission-guard.js`, `obs-control-my-scans.js`.
- **v1.34.302 was a real bug find**: `coins.mint` holds mint *names*, so the `mint=eq.S` filter matched nothing — the bucket price lane had been dead for every US mintmarked coin.
- **v1.34.301 was a same-day revert** of v1.34.300, which broke every lookup.

On the OBS side: media preload before hot-swap (fixes overlay flicker), pop font 11px→20px, an OCR-targeted `lkup.info/cert/?c=…` line on the card, dealer-scoped broadcast lane `obs:<obs_key>` replacing six unfiltered `postgres_changes` bindings, and `/obs` / `/obs_qr` now redirect to the signed-in dealer's keyed URL instead of bouncing anonymous sessions to `/dashboard`.

**Realtime tenant terminations got a root cause.** The overlay disconnecting mid-show was the visible symptom. 24h of `realtime_logs`: 104× tenant queue timeouts, 46× pooling replication errors, then **53× `Tenant vsotvatntzlrzrhemayh has been terminated: :shutdown`** — which drops every websocket for the project at once. Cause: at rest with no show running, `realtime.subscription` held 32–36 rows and **every single one had `filters = {}`**. Overlay and obs-control are fixed. `AdminObsControl` still has ~5 unfiltered, `AdminLiveFeed` and `AdminOutputLog` 4 each, the extension service worker 3. `Cert.tsx` is fully filtered and is the model to copy.

Label printing was removed from all unauthenticated surfaces — gated at the capability, not just the control, so a signed-out browser with a stale localStorage flag can't emit print requests.

---

## 6. Scan performance — real numbers, and a decoder bake-off

Aug 14–15. Three fixes: stopped a camera restart storm, killed `autoScan` loop forking, and dropped cadence to 15/sec. Then the decode worker gets prewarmed at camera-ready instead of at first miss. Measured on live prod: **Safari/iOS first decode 3,435ms → 416ms**.

A decoder bake-off ran ZXing vs zbar-wasm (RGBA and greyscale) across a distortion matrix. Result is honest and unflattering: ZXing 52.4% hit rate at 12.5ms average, zbar 57.1% at ~28ms. Neither handles the realistic handheld cases (`noise 0.2 + blur 1.5 + rotate 8° + contrast 0.7` misses on all three). The harness also flagged three of its own rows as harness errors rather than decoder misses — worth keeping, that's the kind of self-correction that makes a bench trustworthy.

Artifacts in `audit/perf/`.

---

## Also shipped, smaller

Council/AI pricing changed shape: the emit gate no longer withholds (sparse coins emit anyway — measured on a 400-coin sample, 190 previously emitted nothing and 184 of those now do), the emit body went from three fields to four (`sparse` added), thin bundles may use `web_search`, and guards now **hold** verdicts with `is_current=false` rather than discarding them. New `reference.grade_shape` (5,964 rows, learned grade→price shape) and `public.project_guide_tower`. The sanity check that made grade_shape credible: `$1 SILVER EAGLE` comes out 1.00× at every grade while 50C is 2.40×/6.01× at MS65/MS66 — the method rediscovers the bullion/numismatic split unprompted.

Desktop scanner: NDI phone cameras restored, explicit per-slot start/stop, auto-print gated on canonical cert readiness, scans unified through the Supabase pipeline, print dedup race fixed.

Guards added: all-zero cert numbers rejected in the parser, the DB and the extension; `enqueue-enrichment` can no longer first-mint a cert; grader scrapes gated on positive page evidence; `coin_current` and `coin_current_with_ownership` promoted to HARD-dead so a new reader can't be reintroduced.

---

## Three things you should know that aren't good news

**The frontend deploy is behind.** I checked the served bundle by content, not by commit. `Dealer-D_rSwTht.js` on lkup.info right now does not contain `"Limits are not enforced during alpha"` or the `On roadmap` tags from commit `5eaf6c034` (Aug 15 03:29), and the served `CameraInput-C4oWmWjM.js` contains no `prewarm` marker from the Aug 15 01:15 scan fix. `UserRecentScansRail` (Aug 14 04:15) *is* served. So live is somewhere around Aug 14 midday — roughly the last 24–30 hours of frontend work is committed and pushed but **not deployed**. Git push does not deploy; the Lovable button still needs a click.

**`audit/LOOP_LEDGER.md` is stale.** CLAUDE.md names it the sole live source of truth for architecture and priorities. It was last modified **Jul 26** — three weeks ago, and it missed the entire spine-convergence effort. The documents that are actually current are `audit/spine-facet-convergence-plan-20260812.md` and the two ADDENDUM blocks in `agents/scheduled/update-state-diagrams/SKILL.md`. Either promote those or refresh the ledger, because right now the doc that claims authority is the one that knows least.

**The migration count is a loaded gun.** Pre-push GATE 5 now blocks pushes because the Supabase integration's `prod` branch *is* the production project (`is_default=true`, `parent_project_ref` = itself — not a preview), so its Migrate step runs `db push` against prod. It is held shut only by a failing check (`MIGRATIONS_FAILED`, remote versions not found locally). Anyone who "helpfully" reconciles that drift to turn the check green releases every local-only migration onto production at once. That is now documented in the hook itself with a `MIGRATION_GATE_ACK` override for deliberate releases. Given roughly 90 new migrations went in this week alone, that gate is the only thing standing between you and a very large silent swing.

---

## Open, high-priority, filed

`mv_coin_pricing_evidence` fabricates grade labels — `grade_key` concatenates `desig` onto bare-numeric grades, producing `MS12`/`MS40`/`MS4`. **42,821 phantom rows project-wide, 4,191 on 323 coins you hold slabs for.** The *values* are correct and verified against CoinFacts; only the labels are wrong. Paired defect with the same root: `emitForCoin`'s strike-prefix matcher is `^(MS|PR|PF|SP)`, so a circulated grade like `F12` yields an empty prefix and matches any row with the same grade number — including the fabricated `MS12`. Both filed, neither fixed, and the fix needs your eyes first because that view feeds cert pricing, council evidence and the tower.

Also open: rebuild `project_guide_tower` to return the sibling-set bucket matrix rather than one row's tower; build the variety-vs-parent inversion detector (**552 of 1,749 buckets price the variety below its own parent date** — that's evidence the guide is thin, not that the coin is cheap); re-key `grade_shape` off real sibling sets; and an admin-only prose "how we got this price" surface you asked for on Aug 14.

One thing filed as *do not fix*: the 3,369 NGC-id and 66 PCGS-number `coins`-vs-`spine` differences are **hierarchy levels, not conflicts** — die variety vs major variety. 1810 50C O-104 has `coins.pcgs_number=39409` (die variety) and `spine.pcgs_number=6095` (date); PCGS's own page lists 39409 *under* 6095. This was initially reported as a 69% identity-conflict crisis and you disproved it with CoinFacts. A future run that "reconciles" them destroys the variety layer.

# Heimdall Nov-2023 demo deck + PersonasCHD.pdf — recreated through Heimdall 3.0

Open `out/report.html`. 33 charts, each rendered RECREATED | ORIGINAL with a grade, the row-coverage
numbers, the landmark checks and the axis provenance. Re-run: `python3.13 recreate_charts.py` (read-only;
~6 min; `--only id,id` for a subset).

## What was recovered from the 2023 material

| artifact | what it holds |
|---|---|
| `defs/nov2023_hopscotch_calcs.md` | all 145 calculated fields of `Heimdall Nov 2023_Hopscotch.twb` (the deck's source workbook; 790 MB, streamed) |
| `defs/audiences_from_tableau.json` | 100 pole formulas translated mechanically to Heimdall seed grammar (`term*w`, `-term`) by `tableau_formula_to_seeds.py` — a linear-form evaluator over Tableau's `zn(avg([anchor])-c)*w` grammar |
| `defs/nov2023_groups.json` | the ROW SOURCES: 97 Tableau groups/sets with members (INC 5000, First Names, IMDB, Actors, Banks, News/Fake-news outlets, YouTube channels, Influencer handles, Google Ads placements, Clio keywords…) |
| `defs/audience_catalog.json` | 39 audiences: 13 Tableau-exact (Political Spectrum, Hopscotch, Income, Average Person, SMB Owner, Tab Flow/ABL/Existing/Tabbank.com, Attorney/Law, Mormon Culture, LDS, Female Contrast) + 26 CHD segments/traits/personas authored from the 2017-18 methodology decks (slide references in `basis`) |
| `defs/coverage.json` | how much of each 2023 row set and anchor set is grounded in today's corpus |
| `chart_specs.py` | per-slide spec: row source, axes, landmarks read off the original, notes |

Key 2023 definitions, verbatim: **Political Spectrum** = 8 right anchors (+) vs 8 left anchors (−), Mother Jones/Newsmax ×2;
**Hopscotch** = 112-anchor small-business-banking persona (AR financing, ABL, treasury mgmt, business loans, online business
banking; accountants and consumer-loan seekers subtracted); **Average Person** = mean correlation with the single-character
searches a, b, c, d, e, f, i, l, m, 3; **Ubiquity** = sqrt(volume / average-person); **Segment Contrast** = segment·.22 − avg·.75.

## How the charts are scored

Axes are the 2023 formulas evaluated as Σ w·Pearson(keyword state z-vector, anchor state z-vector) on the engine's state-
fingerprint plane (`artifacts/geo_corr/<cycle>/fps_z.f32`, 944,329 grounded keywords × 51 states) — the statistic the 2023
charts used, on today's corpus. The same formulas are minted as Matrix columns (`audience:saved:*-2023`); agreement with
Matrix h on the 156k base rows where both exist: PS +0.89, Hopscotch +0.87, Income +0.84, Average Person +0.83, SMB Owner
+0.89. The Matrix is not used as the primary source yet because the 2023 entity rows live in the addendum (row ≥ 2,458,762)
and freshly minted pole columns are base-only until the next cycle unions the declared seed columns
(`phase1/artifacts/columns/demo2023_axis_seeds.json`, `chd_persona_seeds.json`, `legal_saas_seeds.json`) — todo #14723.

POI charts use `artifacts/poi/<version>/poi-fingerprints.npz` (1.3M POI terms × 53 states, physical-location counts) —
state SHARE z-scored, Pearson vs the same anchors; Ubiquity there is log10(locations).
Google audience charts (slides 7-8) place each Google segment at the weighted mean of its member keywords' scores, members
from `staging/audience_formulas.json`, exactly how the 2023 workbook placed them.

## Speedbumps hit and fixed (Turso #14718-#14725)

1. `compose_audience.py` argparse read `-cnn.com*0.5` as an option → every formula with a negative term died (exit 2). Idents now follow `--`.
2. A pre-`parse_term` demo registered 14 NaN placeholder columns named `gun safe*0.5` → `scripts/fix_weighted_debris_poles.py`.
3. `mint_audience_namespace.py` counted NaN placeholders as minted → Political Spectrum composed NaN on every row; refills with overwrite now, all-NaN audience columns re-compose.
4. `GET /api/audiences` = DuckDB read on the request path (46 s + 118 s loop stall) — #14721 open.
5. save → background mint dies on every demo restart — the idempotent namespace minter is the durable path (#14722).
6. Composed Matrix audience columns are collinear across the 6,159 Google columns (r=0.99 even after regressing Average Person out) — #14724 open.

## Still open
* CHD personas chart: 225 seeds (byu, general conference, relief society, r/exmormon, ces letter…) are queued for onboarding; rerun `--only 35_chd_personas` once grounded (#14725).
* Websites (4): the 2023 rows were Clio ad HEADLINES; 58 legal-software search phrases are queued so the chart can be built from real search terms.

## Onboarding lane state (2026-09-06 14:12, Turso #14877 / #14725)
The CHD + legal seeds were queued three ways (prefetch_onboard next_api 19:36, master spool, seed_onboard interactive 14:12).
Measured: `/api/onboard_status` → CHD 2 grounded / 22 no_volume / 201 pending; `kw_search 'general conference'` → requests=0
since 2026-08-23. The interactive lane is SERIALISED, not dead: demo_server.py:3200-3275 — the ingest's all-res pass parks
(cap, then one geo request) while ONE interactive pull is in flight (`YIELD-DIAG pid=70771 inflight=1 pool=16369
tiers={0: 4785, 1: 11584}`); 4,785 tier-0 keys are queued ahead of these 283 in the ingest's own pool (the demo's
/api/pipeline shows a different process's copy — read the code comment before calling it a deadlock; three sessions
already did on 2026-09-06). Throughput is one 51-state batch at a time, so these seeds ground when the lane reaches them.
Scheduled task `heimdall-chd-chart-rerun` (2026-09-07 09:30) rebuilds both charts as soon as they do.

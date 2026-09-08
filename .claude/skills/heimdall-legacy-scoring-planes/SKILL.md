---
name: heimdall-legacy-scoring-planes
description: Score any keyword, POI, or Google-audience list against a Heimdall audience formula using the planes that can actually answer — the state-fingerprint plane (2023's own statistic), the POI state-share plane, Google-audience member means — and report Matrix-h agreement. Use when Matrix h is NaN for the rows you need (addendum rows, freshly minted poles), when building Political-Spectrum × persona scatters, POI ubiquity charts, or a "does the new engine agree with the old method" number.
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset, UPDATE THIS SKILL with an `If you are [Platform]` block.

# Legacy scoring planes (read-only; no service, no DuckDB)

Implementation: `Engine`, `poi_plane`, `poi_score`, `run_gads` in
`~/github/ammonfife/heimdall3.0/00_client_demonstrations/chart_recreation/recreate_charts.py`. phase1 =
`06_scheme_L_2026/phase1`, python `~/.pyenv/versions/3.13.7/bin/python3.13`.

## Why not just `m.column(...)`
Matrix h is a lookup — but a freshly minted pole column has values only for the BASE rows (n_base = 2,458,762 on
cycle 20260828T183159); the 729k ADDENDUM rows (where domains like pinterest.com, tiktok.com and most 2023
entities live) read NaN until `tools/build_addendum_poles.py` can resolve the pole's members as TOKEN columns
(declared via `artifacts/columns/*.json`, unioned at the next cycle). Check `m.row_of(t) >= m.n_base` before
trusting a NaN. Union-wide mint = Turso #14374.

## Plane 1 — state fingerprint (keywords)
`artifacts/geo_corr/manifest.json` → `<cycle>/fp_keywords.json` (944,329 keywords), `fps_z.f32` memmap
(N × 52 float32; `geo_order.json` = 51 states + "United States", the last column is constant 0 — drop it),
`geo_axis.json` = Google geo ids in the same order. Rebuilt daily.
```
Z = fz[:, :51]; Z -= Z.mean(1, keepdims=True); Zn = Z / ||Z||     # row-normalised → dot = Pearson r
A = Zn[anchor rows]; w = weights (parse_term)                       # signed, weighted anchors
score = (Zn @ A.T) @ w / |w|.sum()                                   # Σ w·r(keyword, anchor) — the 2023 formula
```
Skip anchors whose Zn row is non-finite (zero-norm fingerprints — they poison every score with NaN).
Utah share / "Utahish" = `fz[:, geo_order.index("Utah")]`. Volume per keyword: `m.row_of(k)` → `m.row_volume`
(row-aligned memmap, −1 = never measured → draw hollow, never size 0).

## Plane 2 — POI state share (places)
`artifacts/poi/<latest osm-*>/poi-fingerprints.npz`: 1,325,263 POI terms; CSR `poi_state_{data,indices,indptr}`
(counts of physical locations per state, 53 cols), `poi_state_google_geo_ids` + `alignment_mask` align to the
keyword plane's `geo_axis.json`. Keep POIs with ≥3 locations (84,644). Share = count / state total, row-normalised
and z-scored, then the same anchor Pearson. Ubiquity for a POI = log10(locations) (2023 used
sqrt(volume/avg-person)); draw the axis reversed (2023 put 5000% on the left). National chains land LOW on an
SMB-banking persona, independents high — that is the check.

## Plane 3 — Google audiences (segments as keyword groups)
`staging/audience_formulas.json["formulas"]["gads:user_interest:<id>"]` = member `{set_key, weight}` lists
(lock-free artifact, 6,161 formulas); labels from `artifacts/h/<cycle>/col_labels.json`. Place each segment at
the weighted mean of its members' Plane-1 scores, size = Σ member volume — how the 2023 workbook placed them.
Do NOT correlate Matrix gads COLUMNS against audience columns: they share one factor (PC1 = 74.6% of variance,
r −0.88 with the Average Person pole) and any two audiences come out r≈0.99 even after regressing it out.

## Derived axes (client side)
Average Person = single-character anchors a b c d e f i l m 3 (all grounded). Segment Contrast: 2023 used
(segment·.22 − avg·.75)·2 on Tableau's scale; on the fp plane both terms are ±0.3 Pearson means and the fixed
constants let avg dominate (measured r(contrast, avg) = −1.00) — regress instead: `c = s − β·avg`,
β = cov(s,avg)/var(avg), and report β. Ubiquity (keywords) = sqrt(volume / |avg|) / p99.

## Agreement check (always report it)
Where a Matrix column exists: `r = corrcoef(h[base rows], plane_score[same rows])`. Measured 2026-09-05 on
156,567 base rows: Political Spectrum +0.893, Hopscotch +0.869, Income +0.839, Average Person +0.831, SMB Owner
+0.891, Tab Flow +0.782, Tab ABL +0.757. Below ~0.7 means the formula did not compose the way you think.
Google gads Matrix columns vs their own member means: median r −0.28 (2026-09-06) — those columns are not a
reference, the member means are.

## Acceptance = landmarks, not r²
Take dots off the original chart with their half (`"x+y-"`), test against the medians, and print pass/FAIL/absent.
Expect r(x,y) ≈ +0.7–0.85 on Political-Spectrum × persona scatters (the 2023 charts all had that diagonal);
≈0 on ubiquity × persona. Drifts are findings: write them on the chart.

## Platform blocks
### If you are Claude (Cowork / Claude Code)
Memmaps are on the real Mac; the sandbox mount sees them read-only too (`/sessions/*/mnt/heimdall3.0/...`) but
run heavy numpy on the Mac (Desktop Commander) — 944k×51 fits in RAM (200 MB); 84k POIs × 51 too.
### If you are Gemini / Codex
Same numpy; scipy.sparse for the POI CSR.

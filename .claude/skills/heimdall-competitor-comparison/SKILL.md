---
name: heimdall-competitor-comparison
description: Compare a client against its competitors (or one customer segment against others) in Heimdall — the 2023 "Different Tab Customers" small multiples, the "Consumer Finance Landscape" scatter matrix, segment-vs-segment contrasts, and per-competitor audience profiles — with the Average-Person factor removed so the comparison is real. Use when Ben asks "how does <client> compare to <competitors>", "which segment is most distinct", "contrast <segment A> vs <segment B>", or a deck needs a competitive landscape page.
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset, UPDATE THIS SKILL with an `If you are [Platform]` block.

# Competitor / segment comparison

Three 2023 forms, all recreated 2026-09-05 (`00_client_demonstrations/chart_recreation/out/32_*.png`, `33_*.png`):
1. **Small multiples** — one panel per segment (X = segment h, Y = the persona of interest, color = Income), a fit
   line per panel. Read the SLOPES: SMB Owner 0.94, Tab Flow 0.51, Tab ABL 0.66, Average Person NEGATIVE — the
   sign of the last panel is the sanity check (a persona that rises with "everyone" is popularity, not a segment).
2. **Scatter matrix** over a competitor landscape (fintech domains: viobank, dwolla, exodus, icard, get.com…) —
   every segment against every other; the off-diagonal blobs show which segments are the same population.
3. **Segment Contrast** = (segment·.22 − average_person·.75)·2 — the 2023 workbook's way of subtracting the
   mainstream factor before comparing. Required: Matrix audience columns share one component (PC1 = 74.6% of
   variance across the Google columns, r −0.88 with the Average Person pole); raw column-vs-column Pearson gives
   r≈0.99 between ANY two audiences. Compare on residuals or on the fingerprint plane (r≈0.8).

Segment Contrast is also the general mechanism for any axis that is inherently client-specific rather than a
standing menu item — competitor-vs-competitor, product-vs-product, persona-vs-persona. See
`heimdall-comparison-axes` for the full axis menu and the rule for when to build a Segment Contrast here
versus a reusable Plane-1 anchor in `heimdall-client-deck`.

## Procedure
1. Landscapes: the client's competitors as a landscape (`heimdall-add-landscape`; brand + domain surfaces both),
   plus each competitor's CUSTOMER audience if definable (`heimdall-create-audience` from their vocabulary —
   the 2023 Tab ABL / Tab Flow / Tabbank.com / SMB Owner set is the template, all in `defs/audience_catalog.json`).
2. Score: `POST /api/chart/scatter {"rows": {"landscape": "<competitors>"}, "x": "<segment A>", "y": "<segment B>"}`
   for each pair (or `chart_specs` entries with `panels=[...]` / `matrix=[...]` for the PNG forms). Add
   `"x": "SC"` for the contrast axis.
3. Profiles: `POST /api/audience_profile {"column": "audience:saved:<slug>"}` per competitor audience → top/bottom
   Google segments by family; diff the lists — what one competitor's buyers over-index on that the client's do not
   is the competitive read. `POST /api/geomap {"audience_terms": [...]}` per competitor → where each wins.
4. Distinctness: for segments A, B over a landscape, report corr(A,B) AFTER regressing Average Person out; > 0.9
   means the two definitions describe one population — merge or sharpen the seeds (subtract the shared terms).
5. Write it as movers: "Deutsche Bank / HSBC / Goldman sit left/low; chime.com / go2bank.com right/high" — named
   entities with their numbers, negatives included (6 callouts + 3 negatives per key-insight page). Draft through
   `heimdall-insight-prompting`'s Competitor-callout writer Gem.

## Checks that catch a wrong comparison
- Both axes are the same thing: r(x,y) > 0.95 on a landscape → one of them is popularity; use Segment Contrast.
- A competitor's audience column is NaN on most landscape rows → those rows are ADDENDUM; score on the
  fingerprint plane (`heimdall-legacy-scoring-planes`) and say so.
- A competitor name with two senses (`Vanguard`, `Ragnar`) → `term_collisions`, subtract the other sense.
- Slope of the Average Person panel positive → the persona is not a segment yet.

## Platform blocks
### If you are Claude (Cowork / Claude Code)
Engine :8000 on the real Mac; PNG small multiples via `recreate_charts.py` (`panels=` / `matrix=` specs).
### If you are Gemini / Codex
Same routes; matplotlib for panels.

---
name: heimdall-geography-read
description: Build and read the geography page of a Heimdall study — per-state scores for an audience or keyword from the state-fingerprint plane, the Utah/regional share view, DMA and site-selection reads, and the sanity checks that catch wrong seeds before any other chart is drawn. Use when a deck needs a map, when Ben asks "where does this audience live / where should they open", or as the first check that a new segment's seeds are right.
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset, UPDATE THIS SKILL with an `If you are [Platform]` block.

# The geography read (the cheapest test that a segment is real)

`POST :8000/api/geomap {"audience_terms": [positive seeds]}` or `{"keyword": "..."}` → per-state values. The map
IS the fingerprint (Ben 2026-07-25, canonical): a keyword returns its own 51-state fingerprint; an audience
returns the per-state MEAN of its seed fingerprints, z-scored across states for display only — scoring never
mixes profiles that way. Save as `geomap_states.json` next to the deck.

## Read it before you chart anything
Top-5 states must be recognisable for the segment or the seeds are wrong — and wrong seeds make every later
chart confidently wrong. LDS/Mormon vocabulary → Utah, Idaho, Arizona. Fintech/SMB banking → NY, CA, TX, FL.
Ragnar-style relay racing → Utah, Colorado, Washington. A flat or scattered map means one of: the seeds are
ungrounded (check coverage first, `heimdall-full-topic-coverage`), the brand word carries a second sense
(`heimdall-term-disambiguation`), or the audience is national by nature — which is itself the finding, and is
said on the slide rather than dressed up as a regional story.

## Regional and share views
Utah share / "Utahish" for a term = `fz[:, geo_order.index("Utah")]` on the fingerprint plane
(`heimdall-legacy-scoring-planes`); the 2023 workbook used `min(Utah, All)/max(All, Utah)` and filtered at ≥2%.
For a POI/site-selection page pair the map with the POI plane (`heimdall-poi-landscape`): the brands that
over-index in the target DMA, by name and location count, are what makes a "where should they open" page
defensible. Deeper resolutions (DMA, district, country) exist but `state` takes ~97% of the Google pull budget —
treat a missing DMA read as not-yet-measured, not as zero.

## Slide form
One map, one paragraph of named states with their numbers, and the negative read ("nothing in the Northeast").
Never present a map whose audience column is NaN on most rows — mint first (`heimdall-audience-import`). If the
seeds are under ~80% grounded, the map is a hypothesis: say so on the slide and schedule the re-check.

## Checks
- Same audience, two surfaces (brand vs domain seeds) should map to the same states; if they diverge, one
  surface is carrying another sense.
- A segment whose map matches the Average Person map is popularity, not a segment — subtract the baseline
  (contrast) and re-read.
- State ranks move slowly; a map that changes shape between cycles means the seed set changed, not the country.

## Platform blocks
### If you are Claude (Cowork / Claude Code)
Engine :8000 on the real Mac (Desktop Commander); the fingerprint memmaps are readable directly for the share
views (`artifacts/geo_corr/[cycle]/fps_z.f32`, `geo_order.json`).
### If you are Gemini / Codex
Same route via `run_command`; numpy for the share views.

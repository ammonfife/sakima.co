---
name: heimdall-poi-landscape
description: Build the Points-of-Interest charts in Heimdall — persona score × Ubiquity for 85k+ physical-location brands, the zoomed top-persona view, the Utah/regional-share view, and Segment-Contrast variants — from the OSM POI state-share fingerprints. Use when Ben asks for "points of interest", "which stores/places index for <audience>", a regional (Utah) POI read, or a site-selection page like Belle Medical.
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset, UPDATE THIS SKILL with an `If you are [Platform]` block.

# POI landscapes (slides 24–27 of the 2023 deck, recreated 2026-09-05)

Data: `phase1/artifacts/poi/<latest osm-*>/poi-fingerprints.npz` — 1,325,263 POI terms, per-state physical
location counts (CSR `poi_state_*`, 53 columns, `poi_state_google_geo_ids` + `alignment_mask` align to the
keyword plane's `geo_axis.json`), plus DMA / district / country slots. Implementation: `poi_plane()` and
`poi_score()` in `00_client_demonstrations/chart_recreation/recreate_charts.py`; API: `POST /api/chart/scatter
{"rows": {"poi": true}, "x": "UBQ"|"SC"|"UT", "y": "<persona>"}`.

## The statistic
Share of each state's POIs → row-normalised, z-scored → Pearson with the persona's anchor state z-vectors
(same anchors, same formula as the keyword plane). Keep POIs with ≥3 locations (84,644). Ubiquity =
log10(locations) drawn REVERSED (2023 put 5000% on the left); the 2023 formula sqrt(volume/avg-person) mixed
search volume in — locations is the honest version of "how everywhere is this brand".
Variants: X = Segment Contrast (hop·.22 − avg·.75)·2 (slide 27), zoom to the top-3% persona POIs (slide 25),
Utah view = share of a brand's locations in Utah with a ≥2% filter (slide 26).

## The reads that must hold
National chains (McDonald's, Subway, Starbucks, Walmart, Target, Best Buy, T-Mobile) sit LOW on an SMB-banking
persona; churches, independents, credit unions and local services sit high; r(ubiquity, persona) ≈ 0 (2023:
+0.02) — a strong slope means the persona is popularity. Landmarks: Deseret Book / Maverik / Harmons high on the
Utah axis; the Utah chart's names should be recognisably Utah.

## Use in a deck
Site-selection pages (Belle Medical form): take the client's persona, list the POIs that over-index in the
target DMA (`POST /api/poi/audience_map`, `POST /api/poi/areas`) and pair the scatter with the map. Read the top
movers by name and volume of locations; never present an all-NaN persona (mint first — `heimdall-create-audience`).
The explore route (`POST /api/explore sources=["poi"]`) needs the persona's POI slots minted; if it answers
`poi grounded: 0`, use the plane above.

## Platform blocks
### If you are Claude (Cowork / Claude Code)
scipy.sparse + numpy on the real Mac (`~/.pyenv/versions/3.13.7/bin/python3.13`); 84k×51 fits easily.
### If you are Gemini / Codex
Same.

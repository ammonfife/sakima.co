---
name: heimdall-full-topic-coverage
description: Get a TOPIC fully covered in Heimdall — harvest its whole vocabulary (entities, phrases, questions, handles, subreddits, domains, POIs, Google segments), measure what is grounded / a fingerprint row / a Matrix row / a column, declare and queue the rest, and re-measure until the charts and audiences for that topic stand on the corpus. Use when Ben says "full coverage for <topic>", "make sure the engine knows everything about <client/topic>", "why are the CHD seeds cold", or before any deck whose seeds ground below ~80%.
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset, UPDATE THIS SKILL with an `If you are [Platform]` block.

# Full topic coverage

Route: `POST :8000/api/topic/coverage {"topic", "terms": [...] | "landscape": "<name>" | "audience": "<name>",
"declare": true, "queue": true, "tier": "interactive|machine"}` → per term: `grounded, no_volume, in_fingerprint,
matrix_row base|addendum|none, is_column, volume`; summary percentages; with `declare` it writes
`artifacts/columns/<topic>_seeds.json` (the next cycle unions these as token columns), with `queue` it
front-of-queues the cold terms.

## 1. Harvest the vocabulary — every unit type, by sense
Build the sense × axis grid first (WORKED_EXAMPLE_RAGNAR.md): `Ragnar (race) / (company) / (norse)` × topic /
affinity / in-market / role; the empty cells are as informative as the filled ones. Then per cell:
- entities: brands, domains, people, places (POI names via `artifacts/poi/*/poi-fingerprints.npz keywords`),
  competitors, referral sites;
- phrases: 1..10-grams from the client's copy / site (`POST /api/onboard {"url"|"text"}` extracts all units);
- questions (`why do…`, `can I…`), handles (`@…`), subreddits (`r/…`), Google segments that already exist
  (`GET /api/audience_namespace?q=<topic>` — 6,159 gads columns, no onboarding needed);
- legacy lists: Tableau groups from the 2023 workbooks (`defs/nov2023_groups.json`), the CHD topic lists
  (`extracted_text/CHD Data Science_*.md`).
Write them as BARE lowercase search terms — not ad headlines, not taxonomy labels.

## 2. Measure
`topic/coverage` on the whole harvest. Read four numbers, in this order: `pct_grounded` (has state data — the
floor), `pct_in_fingerprint` (scorable on the 2023 statistic today), `pct_addendum` (Matrix rows whose new pole
values wait for a cycle union), `pct_column` (usable as an anchor/seed of a formula right now).
`no_volume` = Google answered null: a real answer (run-once rule) — do not re-queue, find another surface.

## 3. Declare + queue, then WAIT correctly
`declare: true` is what makes the next cycle mint token columns for the topic (Ragnar pattern,
`carry_poles_forward.py` globs `artifacts/columns/*.json`). `queue: true` puts the cold terms on the
front-of-queue lane. That lane is SERIALISED — one 51-state pull in flight at a time, thousands of tier-0 keys
ahead; `kw_search?mode=exact` showing `requests=0` means "not reached yet", not dead
(`demo_server.py:3200-3275`; three sessions misread this on 2026-09-06). Re-measure with
`POST /api/onboard_status` or `topic/coverage`; never re-queue what is already pending; schedule the re-check
(scheduled task) instead of watching.

**Always pass `"tier": "interactive"` explicitly** for a real client/topic coverage pass -- do not
rely on a default. `heimdall-audience-import`'s 2026-09-06 measurement found the sibling
attribution field (`prefetch_onboard`'s top-level `source`, written to `master_keyword.priority_source`,
the field `PRIORITY_TIER_BY_SOURCE` maps to a tier) had ZERO rows for several real categories because
the calling code left it unset -- an unattributed queue call silently lands at machine tier behind
whatever bulk sweep is running, not the front of the line. `topic/coverage` has its own `tier` param
so this specific route does not depend on that mechanism, but the lesson is the same: an onboarding
call with no explicit priority signal defaults to the slow lane, silently. Never queue without stating
the tier you need.

## 4. Close the loop
When `pct_grounded` ≥ 80%: define the audiences/traits for the topic (`heimdall-create-audience`,
`heimdall-create-trait`), add its landscapes (`heimdall-add-landscape`), chart them with landmarks, and record
the coverage table in the client CHART_AUDIT.md. Below 80%: say so on the slide — a thin axis is a hypothesis.

## Reference numbers (2026-09-05/06)
CHD/LDS topic: 225 authored seeds → 2 grounded, 22 no_volume, 201 pending after 17 h (behind 4,785 tier-0 keys);
legal-software: 59 seeds → 4/1/54. The 2023 axes: Political Spectrum 16/16, Hopscotch 109/112, Income 27/27,
Average Person 10/10 grounded — the corpus is strong on 2020-23 commercial vocabulary, thin on religious and
niche-professional vocabulary.

## Platform blocks
### If you are Claude (Cowork / Claude Code)
Engine on the real Mac; bulk harvests via `nohup`; use the scheduled-tasks tool for the re-check so it does not
depend on a human.
### If you are Gemini / Codex
Same routes; use your scheduler for the re-check.

## Semantic coverage diagnosis (measured 2026-09-06)

`POST /api/seasonality/semantic_match` returning 404 with no embedded audience terms is a genuine
coverage finding: harvest and queue those terms instead of retrying. Keep that separate from a NaN
inside an otherwise covered semantic row, which can poison a centroid and produce an empty pool.
The first is an onboarding gap; the second is a cycle-fill/data-quality gap.

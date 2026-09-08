---
name: heimdall-create-audience
description: Define a Heimdall AUDIENCE — a population (segment, customer persona, lookalike) as a register-scoped, signed seed list — through the engine API, get it minted durably, and prove it. Use when Ben says "create an audience/segment/persona for X", "make a lookalike of <client's customers>", "define the <brand> buyer", or when a chart needs a Y axis that is a population rather than a trait.
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset, UPDATE THIS SKILL with an `If you are [Platform]` block.

# Creating an audience (a population)

Route: `POST :8000/api/audience/define` (routes/legacy_charts.py) — body
`{"name", "terms": [...], "description", "basis", "register": "affinity|in-market|topic|demographic|life-event", "source"}`.
It saves the record (`audience:saved:<slug>`), declares the bare seeds in `artifacts/columns/<slug>_seeds.json`,
queues cold seeds front-of-queue, and starts the durable out-of-process mint. Response carries `coverage`
(`grounded/no_volume/pending`), `cold`, `mint`. The legacy UI path `POST /api/save_audience` still works; the
column-first path `POST /api/audience/create {"positive":[[...]],"negative":[[...]]}` is for when you already hold
the columns.

## 1. Pick the axis before writing a seed (AUDIENCE_AXIS_REGISTER.md)
`chess.com` is an affinity, `buy chess set` is in-market, `en passant rule` is a topic, `chess.com careers` is
firmographic — four different populations. One register per audience; split a mixed list into two audiences.
The 2023 *Hopscotch persona (112 anchors) is the model of a well-built in-market population: blocks of intent
phrases with block weights (AR financing ×6, treasury management ×5, small-business loans ×8) and SUBTRACTED
neighbours (accountants, consumer-loan seekers, SBA-disaster) — `defs/audience_catalog.json` has it verbatim.

## 2. Seeds
- Client vocabulary ranked by Google volume: the 3–5 terms carrying >90% of volume are the core; long-tail seeds
  add noise. 20–120 seeds for a persona; a lookalike from a customer list = the customers' names/domains.
- Disambiguate: `POST /api/term_collisions {"terms":[...]}` — a live collision (Ragnar → vikings 0.95) means add
  the other sense as a NEGATIVE (`-ragnar lothbrok`). Signs and weights ride the term (`term*2`, `-term*0.5`).
- A persona is a CLUSTER (dot = mean of members, size = Σ volume); define it as a small keyword set and score its
  members, do not average it into a pole unless it is also an axis.

## 3. Define, then check the answer
```
POST /api/audience/define  →  coverage.grounded should be ≥ 80% of seeds
POST /api/topic/coverage {"audience": "<name>"}   # per-seed: grounded, in_fingerprint, matrix_row base|addendum, is_column
```
Cold seeds are already queued (interactive tier) and declared; the lane is serialised (one 51-state pull at a time),
so check back with `POST /api/onboard_status` rather than re-queuing. Never substitute a different sense to fill a gap.

## 4. Prove it with a chart, not a number
`POST /api/chart/scatter {"rows": {"landscape": "<category>"}, "x": "Political Spectrum (2023)", "y": "<name>",
"landmarks": [["<entity>", "y+"], ...]}` — the audience must place known entities where a human would (national
chains LOW on an SMB-banking persona; law-firm names LOW on a legal-self-help audience). Also
`POST /api/audience_profile {"column": "audience:saved:<slug>"}` for the Google-segment read, and
`POST /api/geomap {"audience_terms": [...]}` — the top states must be recognisable or the seeds are wrong.

## 5. Verify the column, record the definition
`np.isfinite(matrix.load().column("audience:saved:<slug>")).sum()` ≈ n_base (0 = NaN operands — rerun
`scripts/mint_audience_namespace.py`). Entity rows in the ADDENDUM read NaN until the next cycle union; score them
on the fingerprint plane meanwhile (skill `heimdall-legacy-scoring-planes`). Write the catalog entry with
`basis`; Turso fact for anything measured; a captains-log line if it is client work.

## Platform blocks
### If you are Claude (Cowork / Claude Code)
curl / python urllib against :8000 from the real Mac shell; python `~/.pyenv/versions/3.13.7/bin/python3.13` for
matrix checks; long waits go to `nohup … &` + a log under `~/clawd/logs/`.
### If you are Gemini / Codex
Same routes via `run_command`.

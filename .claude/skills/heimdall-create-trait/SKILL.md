---
name: heimdall-create-trait
description: Define a Heimdall TRAIT — a bipolar attribute axis (Political Spectrum, Income, Female/Male, Risk of Leaving, Conformity, Progressive, Tough Questions…) as a signed, weighted anchor formula, calibrate it, mint it, and prove it with landmarks. Use when Ben asks to "create a trait", "add an axis for X", "make an income/age/political/… dimension", or when a persona study needs the CSC-style dimensions.
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset, UPDATE THIS SKILL with an `If you are [Platform]` block.

# Creating a trait (an axis, not a population)

A trait answers "where on a line does this keyword/person sit"; an audience answers "who". Traits are
BIPOLAR formulas — one pole per end — and become chart axes and colors. Worked, verified examples live in
`00_client_demonstrations/chart_recreation/defs/audience_catalog.json` (`role: axis|trait`).

## 1. Write the two poles as anchor pairs
The 2023 Political Spectrum is the model: 8 matched PAIRS, each a left anchor (−) against a right anchor (+) of
the same kind — news vs news (cnn.com / foxnews.com), magazine vs magazine (Mother Jones / Newsmax ×2), retailer vs
retailer (Whole Foods / Walmart, duane reade / gun safe), org vs org (Lincoln Project / RedState), personality vs
personality (Michael Moore / Ben Shapiro), niche site vs niche site (specialtyfood.com / Drudge Report), donation
intent vs donation intent. Matched pairs cancel the shared "how mainstream is this" factor; unmatched anchors
turn the trait into a popularity axis. Income does the same: private banking / Maldives / "i make 250 000 a year"
against "i make 10 dollars an hour" / "apartments near me 600 or less" / "please help me i need money".
Weights: `anchor*2` for the cleanest pair, `*0.5` for the rest; the sign is `-` on the term. Grammar =
`matrix.parse_term` (`term`, `-term`, `term*w`, `-term*w`). 12–30 anchors; single-word anchors only if they
have one sense (`POST /api/term_collisions`).

## 2. Ground before minting
`POST :8000/api/onboard_status {"terms": bare anchors}` — every anchor should be grounded; a trait built on
2 of 16 anchors is not that trait. Cold anchors → `prefetch_onboard` + declare in `artifacts/columns/<trait>_seeds.json`
and wait; do not substitute a different sense to fill the gap.

## 3. Save + mint + verify
`POST /api/save_audience {"name": "<Trait> (<year>)", "terms": [...], "description": <the pairs, spelled out>}` then
`python3.13 scripts/mint_audience_namespace.py` (durable; the save's background mint dies on restarts). Verify
`np.isfinite(m.column("audience:saved:<slug>")).sum() ≈ n_base`; for addendum rows use the state-fingerprint plane
(skill `heimdall-legacy-scoring-planes`).

## 4. Calibrate with landmarks, then centre
Pick 8–12 entities whose side is not arguable (nytimes.com / foxnews.com; Deutsche Bank / go2bank.com; Ryan Gosling /
Sean Hannity) and check sign and order on the plane you will chart on. Political Spectrum recreated 2026-09-05:
news outlets 5/8, banks 4/6, actors 5/5, law landscape 5/5 in the expected halves, r vs the 2023 Matrix column +0.89.
Report the median so the chart's zero line means "average"; the 2023 workbook added a constant (`+.17)/(8/2)`) for
exactly that — keep it as metadata, not in the seeds.

## 5. Record it
Catalog entry with `provenance`, `basis` (the pairs and why), `n_positive/n_negative`; Turso fact with the landmark
result; the chart that proves it. A trait with no landmark check is a hypothesis.

## Traits that exist (2026-09-05, `audience:saved:*-2023`)
Political Spectrum (16 anchors), Income (27), Average Person (10 single-letter anchors — the mainstream baseline
every contrast subtracts), Female Contrast (42), and the nine CHD dimensions (Belief in Institution, Church
Attendance, Core Doctrine, Cultural Doctrine, Diligence, Conformity, LDS Culture, Progressive, Tough Questions —
seeds still onboarding). Reuse before inventing.

## Platform blocks
### If you are Claude (Cowork / Claude Code)
Engine calls and mints on the real Mac (Desktop Commander), python `~/.pyenv/versions/3.13.7/bin/python3.13`.
### If you are Gemini / Codex
Same endpoints via curl/`run_command`.

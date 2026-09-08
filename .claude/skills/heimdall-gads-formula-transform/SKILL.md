---
name: heimdall-gads-formula-transform
description: Build a 2023-format formula for any Google (gads) audience — coherent core from term × term geo Pearson, in-domain candidate pool from the stored SEM Pearson, geography deciding + or −, weights from both signals, and a harvest list for members with no row. Use when Ben says "transform the gads audiences", "select the seeds and calculate the weights", "why is this audience returning junk", "which terms should be negated", or before any deck that plots Google audiences.
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset, UPDATE THIS SKILL with an `If you are [Platform]` block.

# Building a gads audience formula

`00_client_demonstrations/chart_recreation/gads_build_formulas.py` — `--sample N` prints formulas,
`--all` writes `defs/gads_formulas_v8.json`. Plan of record: `docs/GADS_FORMULA_TRANSFORM_PLAN.md`
section (v); sections (l)–(t.1) are the dead ends, each with its numbers, so nobody re-runs them.

## The pipeline (Ben's spec, 2026-09-06)
> "you build the core, see what non-core terms rise there, plus the score for high sem score, and
> curate +add or -minus plus weights from there"

1. **CORE.** Grounded members → `C = Zn[M] @ Zn[M].T` (term × term geo Pearson) → leading
   eigenvector. Each member's loading, scaled to max 1, **IS its weight** — graded by measurement,
   the same shape as Hopscotch's ×3 / ×0.889 / ×0.444 / ×0.187 tiers. Members below MIN_LOAD are
   off-core: report them, never hide them. Mean pairwise r inside the core is the coherence score —
   Dishwashers 0.857, Payroll 0.574, Legal Services 0.20 (a bag that never cohered, and it shows).
2. **POOL.** Nearest rows by the **stored** SEM Pearson to the core's sem centroid. `rows_sem.f32`
   (base) + `rows_extra_sem.f32` (addendum), row-centred and unit-norm, so a dot IS Pearson —
   do not recompute cosine. This is the in-domain candidate set; **unrelated terms are ignored, not
   turned into foils.**
3. **SIGN — no gate** (Ben 2026-09-06: *"no, no gate"*). A term's sign is simply **the sign of its
   geo agreement**; its weight is **∝ |geo| × sem share**. No quantile decides membership and no
   floor decides sign. The batch build still uses quantiles and that is a known wart — a quantile
   splits whatever list it is handed, so once a pool is picked clean the "top 40%" can cut *below
   zero* and label terms that move AGAINST the core as positives. Measured on Payroll Services:
   `ovation payroll` at geo −0.036 and `alarys.com` at +0.000 admitted as positives. Under the
   no-gate rule they are negatives carrying ~0.02 — what they earned, and harmless.
4. **CONTAINMENT — damping, not a threshold.** general **topic > affinity > intent** (Ben: *"each
   can contain from more specific without polluting the more generalized ones"*). A topic is the
   widest container and subtracts reluctantly (×0.35); affinity ×0.70; intent, the narrowest, at
   full strength ×1.00. It scales a foil's weight and never refuses one.
5. **SCALE against the definition, never the leftover pool.** Normalising by the candidate pool's
   max pins every weight to the caps: Payroll came out with exactly TWO distinct positive weights
   (0.6000 / 0.0000), destroying the graded weighting that is the entire point of the format.
6. **HARVEST.** Members with no fingerprint row → the onboarding list (`heimdall-full-topic-coverage`).
   `gads_emit_harvest.py` closes the loop: 145 share-gated columns (≥4 audiences, 1.3 GiB) plus
   100,914 rows listed separately, because a term needs only a ROW to act as an anchor and earns a
   COLUMN only when many audiences want it — declaring all of them would ask the union for ~924 GiB.
7. **WRITE IT CANONICALLY.** See below — an improvement that does not replace the Google definition
   is a copy nobody reads.

## What a foil actually is
Ben: *"foils are often found at the top … not because they are unrelated, but that they ARE RELATED
but the wrong thing"* and *"we read and judge the NON-seed terms rising to the top, looking for
tangential (not noise) pollution to negate."*

**Payroll Services** — core 28 terms, 380 in-domain candidates:

| | term | weight | geo | sem |
|---|---|---|---|---|
| +ADD | sage payroll | 0.5475 | **+0.934** | 0.792 |
| +ADD | payfit | 0.4301 | **+0.947** | 0.614 |
| −MINUS | paycor | 0.4885 | **−0.386** | 0.821 |
| −MINUS | paychex | 0.4677 | **−0.301** | 0.786 |
| −MINUS | paycom | 0.4586 | **−0.354** | 0.770 |

The negatives are payroll BRANDS: maximally in-domain, moving oppositely. Employees checking a
paycheck and existing customers logging in — not businesses shopping for payroll. That is Hopscotch
subtracting `accounting exam prep` under an SMB-banking pole, found by measurement.

## Rules learned the hard way (all measured, all in the plan)
- **Never grade this by semantic plausibility.** Ben: *"these are not bugs, this is not NLP this is
  understanding EVERYTHING about a core audience."* An investors audience surfacing the ASPCA, The
  Verge and Rome flights is affluence and international travel — a finding. In the BUILD stage
  unrelated terms are noise to ignore; **in the OUTPUT stage that noise is the insight.**
- **Never average the bag.** Collapsing ~55 harvested members into one mean is what destroys the
  signal; term × term geo Pearson over the same members shows the structure plainly. The plane was
  never the problem.
- **Membership is not exclusive.** A term may carry weight in several audiences — 96 terms appear in
  more than one 2023 audience at different weights (treasury management +0.4444 Hopscotch / +0.2315
  Tab ABL). Nothing is removed from anyone.
- **Do not gate on held-out AUC, sibling distinctness, or agreement with v1.** The first rewards
  topical sameness (gads dumps beat Hopscotch 0.681 to 0.601 on it), the second measures a property
  that should not be gated (random pairs sit at |r| 0.69), the third demands the rebuild reproduce
  the defect. Validate with landmarks on a curated landscape, read by someone who knows the
  population.
- **Volume matters.** Unfloored corpus rankings fill with 1.6k-search rarities whose 51-state
  vectors correlate with anything. The 2023 workbook always had `_Volume Visualization` and
  `_Ubiquity` in play.
- **`rows_sem` stores NaN for unfilled rows**, and one NaN row poisons a core centroid to NaN — the
  in-domain pool silently reads 0. Zeroed as a stopgap; Ben: *"assume we will calculate these in the
  cycle."*

## CHD composes differently — do not flatten it
Ben: *"the traits were built off keywords, the segments built off dials of those traits."* Nine CHD
traits (Belief in Institution, Church Attendance, Core Doctrine, Cultural Doctrine, Diligence,
Conformity, LDS Culture, Progressive, Tough Questions) are keyword formulas; a SEGMENT is each trait
dialled −3…0…+3, so the space is 7^9 addressable points, MBTI-style. The 12 "CHD Persona" records
are named points in it. Expressing gads audiences that way is a larger, separate idea.

## Writing the result canonically (Ben: *"it needs to actually write to the canonical gads audience"*)
Building a formula changes nothing on its own. Use **`/heimdall-improve-audience`** for the write —
it takes the definition wherever it currently stands, re-scores inherited seeds so a Google term can
lose weight or flip sign, and rewrites the canonical column.

**Where canonical is NOT:** `staging/audience_formulas.json` is an OUTPUT of
`publish_audience_formulas.py`; editing it changes no column and is erased on the next publish. I
lost a pass to this. The minting chain is
`out/google_targeting_map.json` → `gads_formula_plan()` → `mint_gads_from_columns.py` → the column.

Google's own formula there is 4–10 rows: the anchor at `+2.0` meaning *all my member tokens,
uniformly*, plus **sibling audience columns** at `−0.3333`. That is the r≈0.99 collinearity in one
line, and the format cannot express a term-level foil at all (a non-self `set_key` is blindly
prefixed with `audience:`, so `paycor` resolves to a column that does not exist).

Improvements therefore go to `staging/gads_improved_formulas.json`, which `gads_formula_plan()`
prefers, then:
```bash
python3 scripts/mint_gads_from_columns.py --only audience:gads:topic_constant:724 --overwrite
```
`--stale-only` will NOT publish it: it keys off seed timestamps and cannot see a changed definition.
Verify by reading the column, never by an exit code.

## Platform blocks
### If you are Claude (Cowork / Claude Code)
Real Mac, `~/.pyenv/versions/3.13.7/bin/python3.13`, via Desktop Commander. Engine boot is ~90 s
(fingerprint plane + matrix), so run with `nohup … > ~/clawd/logs/gads_*.log &` and poll — a
3-audience sample is ~3 min end to end. Never write scripts to `/tmp` (it is purged mid-run).
### If you are Gemini / Codex
Same script via `run_command`; numpy only, no service needed.

## Batch reliability lessons (measured 2026-09-06)

Treat a `--all` build as an engine client: serialize it with other high-RSS mint/build jobs, inspect
swap and active batch processes beforehand, and verify a real `api/landscapes` JSON body rather than
an HTTP status alone. A fast run can still be hollow if the demo flaps. Validate the emitted artifact
by inspecting built and `built_low_coherence` audiences together: median expansion and foil counts
must be positive, and empty semantic pools must be explained as genuine coverage 404s rather than
transport failures. The persisted audience list is a list of keyed records, not a mapping; consume
its schema directly instead of inferring it from the printed summary.

---
name: heimdall-improve-audience
description: Improve one Heimdall audience definition starting from wherever it currently stands — current seeds in, better signed/weighted seeds out, written back to the engine as a real audience. Optionally takes Ben's feedback in words. Use when Ben says "improve this audience", "that audience is returning junk", "the negatives are wrong", "make Payroll better", "run another round on X", or after any deck read that produced an opinion about an audience.
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the
> "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset,
> UPDATE THIS SKILL with an `If you are [Platform]` block.

# Improving an audience

`00_client_demonstrations/chart_recreation/gads_improve_audience.py`

Ben 2026-09-06: *"treat the loop as /heimdall-improve-audience so that you can take the current
definition, whatever it is, wherever it ended up as the next starting point and you can pass user
feedback (optional) — improve, audience, feedback."*

## Improvement, not derivation — the distinction that matters
`gads_build_formulas.py` and `gads_curate_recursive.py` **derive**: core from the raw Google
members, eigenvector, weights, pool, from scratch every run. That is right for a first pass and
wrong for a second, because it throws away every judgement the previous pass made.

This **improves**. The current definition is the input; the improved definition is the output; the
output is written back where the next call finds it. Run it ten times across ten sessions and the
definition keeps everything it has learned.

The starting point resolves most-worked-on first, so nothing restarts from zero:

1. `defs/audience_state/<key>.json` — a definition this loop already improved
2. `defs/gads_formulas_v8.json` — the batch build's formula
3. `staging/audience_formulas.json` — the raw Google members, unweighted

The pole is rebuilt from the **current** positives and negatives at their **current** weights. It
is deliberately *not* re-eigen'd: a fresh eigenvector would erase exactly the accumulated judgement
this loop exists to keep.

## The end state is the CANONICAL audience, not a file and not a copy
Ben: *"the end state needs to actually write the audience, no? … with weights and signs"*, then
*"it needs to actually write to the canonical gads audience."*

A state file scores nothing. An `audience:saved:<slug>` copy is worse than useless: it leaves
Google's original as the column every chart, deck and score still resolves, so the good version is
a copy nobody reads. The run therefore rewrites the canonical column itself.

**Where canonical lives** — this cost a wrong turn, so take it from here:

- `staging/audience_formulas.json` is an **OUTPUT**. `publish_audience_formulas.py` writes it from
  DuckDB for the explorer. Editing it changes no column and is erased on the next publish.
- The chain that mints is
  `out/google_targeting_map.json` → `gads_formula_plan()` → `mint_gads_from_columns.py` → the column.
- Google's formula there is **four rows**: the anchor at `+2.0` meaning *all my member tokens,
  uniformly*, and three **sibling audience columns** at `−0.3333`. That format cannot express an
  improvement — a non-self `set_key` is blindly prefixed with `audience:`, so a term foil `paycor`
  would resolve to a column that does not exist.

So the improvement is written to **`staging/gads_improved_formulas.json`**, keyed by pole_column,
and `gads_formula_plan()` prefers it over Google's. Not an edit to `google_targeting_map.json`,
which is rebuilt from the Google segment DB and would erase it. Weights renormalise to a signed
total of 1. Reversible: delete the entry and the next mint restores Google's formula exactly; the
original is also copied into the state file. `--no-write` opts out; `--also-saved` additionally
makes a separate `audience:saved:` copy.

**Publishing the column** is a second step — writing the formula does not move the numbers:
```bash
python3 scripts/mint_gads_from_columns.py --only audience:gads:topic_constant:724 --overwrite
```
`--stale-only` will NOT do it: that keys off seed timestamps and cannot see a changed definition,
so an improved formula is silently skipped as "current with its seeds".

**Verify by reading the column, never by an exit code.** After minting Payroll Services:
`best rated payroll services` +0.512, `cheapest payroll service` +0.506 against `time sheet` −0.383,
`timecard` −0.375, `top payroll services` −0.309 — businesses shopping for payroll separated from
employees checking a paycheck, which a uniform bag plus 70%-overlapping siblings cannot do.

## Feedback is a note to a reader, never a parser input
`--feedback "..."` is recorded in history, replayed at the top of the next round, and **never
parsed**. Ben: *"these are not bugs, this is not NLP."* A sentence like *"the vendor brands are the
wrong population but the listicles are fine"* is addressed to whoever reads the risers next; that
reader then issues the `--add`/`--minus` that implements it. Guessing at the sentence would invent
judgements nobody made. `--drop` exists so no decision is one-way.

## No gate — sign and weight come off the measurement
Ben: *"no, no gate"*, and *"goal is accuracy, not convergence to initial seed."*

A term's **sign is the sign of its geo agreement** and its **weight is ∝ |geo| × sem share**. No
quantile decides membership and no floor decides sign, so nothing is admitted or refused by a
cutoff — a term at geo −0.036 is a negative carrying ~0.02, which is what it earned and is
harmless. The failure this replaced: a quantile always splits whatever list it is handed, so once
the pool was picked clean the "top 40%" cut at −0.036 and terms moving *against* the core were
labelled positive for being least-bad. Grading on a curve still awards an A when everyone fails.

**Containment survives as damping, not a threshold.** General topic > affinity > intent: a topic is
the widest container and subtracts reluctantly, an intent subtracts at full strength. It scales a
foil's weight; it never refuses one.

| register | negative damping |
|---|---|
| topic | ×0.35 |
| affinity | ×0.70 |
| intent (in-market) | ×1.00 |

**Inherited seeds are re-scored every round**, so a term Google assigned may lose weight, gain it,
or change sign. Appending only would make the definition a monument to wherever it started. Scale
the weights against the spread of the definition itself, never the leftover candidate pool — doing
the latter pinned every weight to the caps and produced exactly two distinct values, destroying the
graded weighting that is the whole point of the 2023 format.

## Running it
```bash
# look, decide nothing yet (still writes the unchanged definition unless --no-write)
gads_improve_audience.py --key gads:topic_constant:1250 --no-write

# a human read, which is the actual method
gads_improve_audience.py --key gads:topic_constant:1250 \
  --minus "paycor,paychex,primepayroll" --add "payroll solutions for small business" \
  --feedback "vendor brand terms are logins by existing customers, not businesses shopping"

# mechanical baseline — reproduces the batch build, so it can only ever agree with it
gads_improve_audience.py --key ... --auto --rounds 3

# batch. each audience commits (state + engine write) before the next is touched, so a kill
# at audience 900 costs one audience, not 900
gads_improve_audience.py --all --auto --rounds 2 --resume
gads_improve_audience.py --keys defs/priority_keys.txt --auto --resume
```

## Reading a round
Each riser shows `geo` (agreement with the current pole) and `sem` (in-domain closeness). The
judgement is always the same question: **this term is in the domain — is it the same population?**

A foil is *related but the wrong thing*, never merely unrelated. Payroll Services negates
`paycor`, `thepayrollco`, `top payroll services`: maximally in-domain, moving oppositely —
employees checking a paycheck and existing customers logging in, not businesses shopping. Unrelated
terms are ignored in the build stage; in the **output** stage that noise becomes the insight.

## Before you trust a round
Check coherence on the source record. Lima cohered at 0.122 and the loop confidently negated
`lima travel`, `lima tourism` and `lima tourist attractions` — the audience's own population —
because the eigenvector had latched onto its airport-shuttle members. The mechanics were right; the
bag was never a population. `gads_build_formulas.py` flags these `built_low_coherence`. Harvest and
re-ground before improving one of those; improving a bag only sharpens the wrong pole.

## Platform blocks
### If you are Claude (Cowork / Claude Code)
Real Mac, `~/.pyenv/versions/3.13.7/bin/python3.13`, via Desktop Commander. The demo on :8000 must
be up — SEM comes from the resident engine, never a second copy (a private `rows_sem` block costs
14 GB and exhausted swap on 2026-09-06). Engine boot is ~60–90 s, so `nohup … > ~/clawd/logs/ &`
and poll; batch mode boots once for the whole list. Never write scripts to `/tmp`.
### If you are Gemini / Codex
Same script via `run_command`; numpy plus a running demo on :8000.

## Resume-state reliability lessons (measured 2026-09-06)

Do not record a transport failure as a semantic-coverage result. A genuine semantic 404 is terminal
for that round and belongs in topic coverage; connection failures, timeouts, rate limits, and 5xx
responses require bounded retry and an explicit failure record. Because resume state can otherwise
preserve a hollow round indefinitely, validate error handling by exercising a forced-dead endpoint,
not by compilation alone. Repair any already-persisted hollow state through the skill's canonical
state-repair path, with a backup before changing a durable record.

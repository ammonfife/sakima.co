---
name: heimdall-audience-import
description: Import a catalog of audience/segment/trait/persona definitions (signed, weighted seed lists) into the live Heimdall 3.0 engine — save records, mint the seed and audience columns durably, verify they are finite, and route cold seeds to onboarding. Use when Ben says "import these audiences/personas/formulas", "register the 2023 axes", "mint these as columns", or when a saved audience's column reads NaN.
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset, UPDATE THIS SKILL with an `If you are [Platform]` block.

# Importing audiences into Heimdall 3.0

phase1 = `~/github/ammonfife/heimdall3.0/06_scheme_L_2026/phase1`, python = `~/.pyenv/versions/3.13.7/bin/python3.13`,
engine `:8000`. Reference implementation: `00_client_demonstrations/chart_recreation/{build_audience_catalog.py,
register_audiences.py, coverage_check.py}`.

## 1. Catalog first (one JSON, provenance on every entry)
`{"name", "provenance": "tableau|authored", "role": "axis|segment|trait|persona|baseline", "seeds": [...],
 "basis": "<slide/source text quoted>", "note"}`. Seeds use `matrix.parse_term` grammar — `term`, `-term`, `term*2`,
`-term*0.5`; the sign and weight ride WHATEVER STRING IS THERE -- a bare search term or another audience's own column name (`audience:saved:<slug>`, `audience:gads:<id>`), identically. `parse_term` does not distinguish the two: both are strings, both resolve to `(sign*weight, bare_name)`, and `bare_name` is looked up with `m.column()`. `audience_columns` is explicitly "CLOSED UNDER COMPOSITION" (policy #956): an operand is a column name of ANY provenance (raw term, Google-volume-backed, semantic-only, gads segment, or a previously composed column) or an already-computed column vector, and a composition's output feeds straight back in as an operand to the next one. So `-audience:gads:12345*0.5` is valid seed syntax, signed and weighted exactly like a bare term (verified against `heimdall_core/matrix.py::parse_term`/`audience_columns`, 2026-09-08 -- an audience's terms can themselves be other audiences). Choose the register per axis (affinity /
in-market / topic / demographic) before writing seeds (AUDIENCE_AXIS_REGISTER.md). A persona is a keyword CLUSTER
(dot = mean of members, size = Σ volume), an axis is a formula.

## 2. Coverage before anything else
`POST :8000/api/onboard_status {"terms":[…≤5000]}` → `grounded` per term (has state data). Record per audience
`grounded/total` and the cold list. Anchors below ~2 grounded = the axis is unavailable; say so, don't fake it.
Then queue the cold ones: `POST /api/prefetch_onboard {"terms":[{term,source,score,ngram_n}], "cap":10000,
"next_api":true, "source":"audience_import"}` (one Google request costs the same at 300 or 10,000 terms).
**The TOP-LEVEL `source` is not optional and is not the same field as the per-term `source`.** The route reads
`data.get("source")` and writes it to `master_keyword.priority_source`; the per-term one never reaches the ledger.
That label is what `PRIORITY_TIER_BY_SOURCE` maps to a tier, so an unlabelled POST lands as generic
`prefetch_union` at machine tier and queues behind the 8.2M-row POI sweep. With it, this work is ranked
`interactive`. Use a client-specific value (`"ragnar"`, `"avalara"`) when queueing for one client, so the
work is attributable afterwards — measured 2026-09-06: `priority_source` had ZERO rows for ragnar, avalara,
poles, harvest or audience_seeds, so none of it could be tracked or prioritised. Also declare them in
`artifacts/columns/<consumer>_seeds.json` (flat array of BARE names) so the next cycle unions them as token columns.
Expect the interactive lane to be serialised (one 51-state pull in flight; thousands of tier-0 keys ahead);
`kw_search?mode=exact` showing `requests=0` means the ledger has not been pulled, not that it is dead.

## 3. Save the records
`POST /api/save_audience {"name","terms","description","scope":"global","source":"<who>"}` per audience. Response
`saved/revision`; `minting:true, cold_terms` means the column mints in a background lane. Retry on
RemoteDisconnected / connection refused — peers `launchctl kickstart -k` the demo freely. Column name is
`audience:saved:<slug>` (`heimdall_core.audiences.column_name`); saving twice appends a revision, harmless.

## 4. Mint durably, out of process
The save's background mint dies with every demo restart. The durable path is
`nice -n 10 python3.13 scripts/mint_audience_namespace.py` (idempotent; also scheduled hourly at the end of
`tools/gads_audiences/refresh_audience_map.sh`). It mints every missing seed column in ONE streaming pass
(433 seeds ≈ 10 min, 26–47 GB RSS — check `sysctl vm.swapusage` first), refills all-NaN placeholder columns with
`overwrite=True`, re-composes audience columns that are NaN on every row, and republishes
`staging/saved_audiences.json` (the lock-free snapshot `GET /api/audiences` serves).

## 5. Verify — a column that exists is not a column that answers
```
m = matrix.load(); c = m.column("audience:saved:<slug>")
np.isfinite(c).sum()  # must be ≈ n_base (2.46M) — 0 means NaN operands
```
Then check the ROWS you care about: `m.row_of(term)`; rows ≥ `m.n_base` are ADDENDUM rows and read NaN for
freshly minted poles until the declared seed columns ride a cycle union (the extension only resolves
token-column members). For those rows score on the state-fingerprint plane (skill
`heimdall-legacy-scoring-planes`) and report the Matrix agreement.

## Traps, all measured 2026-09-05
- A demo process older than `parse_term` registers `gun safe*0.5` as a literal column → `scripts/fix_weighted_debris_poles.py`.
- `scripts/compose_audience.py` used `--idents nargs=+`; `-cnn.com*0.5` was read as an option → exit 2 on every formula with
  a negative term. Idents now follow `--`. If a compose logs `unrecognized arguments`, that is the bug.
- `mint_audience_namespace.py` used to count NaN placeholders as minted → Political Spectrum composed NaN on 3.19M rows.
- `GET /api/audiences` used to open DuckDB rw on the request path (46 s + 118 s loop stall, policy #959); it reads the
  snapshot now — if it stalls again, the snapshot is missing: `python3.13 -c "from heimdall_core import audiences as a; a.publish_snapshot()"`.
- Composed Matrix audience columns share one dominant factor (PC1 = 75% of variance across the Google columns = the
  Average Person pole, r −0.88). Never compare two audiences by column-vs-column Pearson without partialling it out.
- Log every defect to Turso (`todo add …`) BEFORE fixing; close with the commit sha.

## Platform blocks
### If you are Claude (Cowork / Claude Code)
Engine, DuckDB and mints run on the real Mac (Desktop Commander); use `nohup … > ~/clawd/logs/<name>.log &` for
anything longer than a minute and poll the log. Tell peers in `~/.claude/projects/-Users-benfife/.inbox` before
restarting the demo.
### If you are Gemini / Codex
Same commands via `run_command`; no restarts without an inbox note.

## Operational concurrency note (measured 2026-09-06)

Before a large mint or audience batch, account for the machine-wide engine budget as well as the
individual command's memory use. A large mint can evict the demo's semantic memmap from cache and
turn otherwise normal engine calls into multi-minute waits. Check current swap and active engine
batches; serialize heavy clients rather than running them together. This is an operations constraint,
not a reason to weaken the audience definition or omit the import.

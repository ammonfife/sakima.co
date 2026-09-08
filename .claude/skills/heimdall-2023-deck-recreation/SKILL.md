---
name: heimdall-2023-deck-recreation
description: Recreate any legacy Heimdall/Cerebro/Tableau-era chart or deck (e.g. "Heimdall Demo Slides.pptx" Nov 2023, PersonasCHD.pdf, CHD/TAB/Clio scatters) through the live Heimdall 3.0 engine with a qualitative acceptance test per chart. Use when Ben says "recreate every chart", "redo the 2023 demo through Heimdall", "does today's engine still tell the same story as the old deck", or wants an old Tableau scatter (X = Political Spectrum, Y = persona, size = volume) rebuilt on the current corpus.
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset, UPDATE THIS SKILL with an `If you are [Platform]` block.

# Recreating a legacy Heimdall deck through Heimdall 3.0

The working pipeline lives in `~/github/ammonfife/heimdall3.0/00_client_demonstrations/chart_recreation/`
(built 2026-09-05 for the 34-slide "Heimdall Nov 2023" deck + PersonasCHD.pdf; 33 charts, report at
`out/report.html`). Read its `README.md` first, then reuse — do not rebuild the pipeline. The same operations are
routes on the engine (`routes/legacy_charts.py`): `POST /api/landscape/add`, `/api/topic/coverage`,
`/api/chart/scatter`, `/api/trait/create`, `/api/audience/define`.

A "simple" old chart is five stacked decisions, and Ben grades on all five ("not an unqualified script that builds
the same charts — look at each with a qualitative lens: does the data make sense, is it similar to these examples,
do we have the seeds we need, what can we substitute"):
1. **Row source** — WHICH entities were plotted (a Tableau group/set, a regex filter, a keyword_id range).
2. **Row existence today** — how many of those strings exist in the current corpus, and what substitutes.
3. **Axis definitions** — the exact 2023 formulas (anchors, signs, weights), not a paraphrase.
4. **Value trustworthiness** — which scoring plane can actually answer for those rows.
5. **Story** — do the same dots land in the same corners? Landmarks read off the original slide are the test.

## Step 1 — find the sources
- Slides: render the pptx to PDF via PowerPoint AppleScript (`save p in "<path>.pdf" as save as PDF`), then
  `pdftoppm -r 130 -png`. Old decks are image-only; extracted_text/*.md will be empty.
- The deck's SOURCE WORKBOOK is a huge .twb in `~/Documents/My Tableau Repository/` or `/Users/data/`
  (`Heimdall Nov 2023_Hopscotch.twb`, 790 MB). Mine it with `tableau-twb-mining`: calculated fields → axis
  formulas; `<group>` members → the exact row sets per chart. `tools/TWB_SEGMENT_DEFINITIONS.md` read only the
  first 50 MB — the key poles (*Hopscotch, _Income, _Average Person) are NOT in it.
- Methodology decks (extracted_text/CHD Data Science_*.md) carry persona/segment/trait definitions in prose;
  author seed sets from them and quote the slide text in `basis`.

## Step 2 — chart_specs.py
One dict per slide: `id, slide, title, x, y, rows, landmarks, note`. `rows` ∈ `{"group": "[Tableau group]"}`,
`{"groups": [...]}`, `{"regex": r"...", "min_volume", "top"}`, `{"corpus_sample": N}`, `{"gads": "user_interest|topic_constant"}`,
`{"poi": True}`, `{"terms": [...]}`; plus `min_scored`, `x2`, `panels`, `matrix`, `chd=True`. Landmarks are
`(term, "x+y-")` — the half of the ORIGINAL chart the dot sat in, judged against the medians.

## Step 3 — axes = audience catalog
`defs/audience_catalog.json` entries carry seeds in engine grammar (`term`, `-term`, `term*0.5`), provenance
`tableau` or `authored` (with `basis`). Register them with `heimdall-audience-import` / `/api/trait/create` so the
same formulas exist as `audience:saved:<slug>` Matrix columns.

## Step 4 — score on the plane that can answer (`heimdall-legacy-scoring-planes`)
The 2023 entity rows live in the Matrix ADDENDUM (row ≥ n_base); newly minted pole columns are base-only and the
addendum extension resolves only token-column members → Matrix h is NaN for exactly those rows (3/40 social
sites scored). The state-fingerprint plane (`artifacts/geo_corr/<cycle>/fps_z.f32`, 944k × 51 states) IS the 2023
statistic; score there and report Matrix-h agreement (r≈+0.83…+0.89 per axis on base rows) on every chart. Flip
to Matrix-first once the declared seed columns (`artifacts/columns/*.json`) ride a cycle union.

## Step 5 — run, then LOOK
`~/.pyenv/versions/3.13.7/bin/python3.13 recreate_charts.py [--only id,id] [--skip-poi]` (read-only, ~6 min).
Grades: GOOD (≥50% rows found, ≥20 scored, ≥60% landmarks pass), PARTIAL, NOT RECREATED. Open the PNGs at full
size. Must hold if the recreation is honest: positive x/y slope like the original (r≈0.7–0.85), news outlets
split left/right by name, big-law left/low vs legal self-help right/high, national chains LOW on an SMB-banking
persona, LinkedIn bottom-left of social sites, Average Person slopes NEGATIVE in the Tab small multiples. Write
drifts as findings (pinterest.com no longer top-right; Tab Existing Business Customers now slopes negative).

## Coverage measured 2026-09-05 (1,500-term samples)
Actors 100%, First Names 99%, IMDB 99%, INC5000 96%, YouTube 91%, Gendered phrases 98%, Fake-news 84%, News 76%,
Banks 75%, Automotive 59%, Law Landscape 41%, Google placements 40%, Google audience labels 12–41% (use the
engine's gads columns as member means instead), Sports 15% of 15.5k (top-400 by volume), Influencer handles 23%
of 52k, Clio ad-headline groups 0.4% (headlines are not search terms).

## Deliver
`out/report.html`, README with speedbumps, commit under `00_client_demonstrations/chart_recreation/`, captains-log,
Turso todos for every defect (log FIRST, then fix). Charts waiting on Google onboarding get a scheduled-task rerun.

## Platform blocks
### If you are Claude (Cowork / Claude Code)
Real Mac shell for engine, DuckDB, PowerPoint; python `~/.pyenv/versions/3.13.7/bin/python3.13`.
### If you are Gemini / Codex
Same scripts via `run_command`; LibreOffice `soffice --convert-to pdf` instead of AppleScript.

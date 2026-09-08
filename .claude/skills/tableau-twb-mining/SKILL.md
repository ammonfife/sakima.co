---
name: tableau-twb-mining
description: Mine Tableau .twb workbooks (including 700 MB+ ones) for calculated fields, parameters, worksheets, and group/set MEMBER lists, and translate Tableau pole formulas (zn(avg([anchor])-c)*w sums) into Heimdall seed grammar. Use when a legacy Heimdall/Cerebro deck's definitions live in a .twb, when "TWB_SEGMENT_DEFINITIONS.md" lacks a pole, or when the row set of an old chart is a Tableau group.
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset, UPDATE THIS SKILL with an `If you are [Platform]` block.

# Mining Tableau .twb workbooks

Scripts (copy from `~/github/ammonfife/heimdall3.0/00_client_demonstrations/chart_recreation/`):
`extract_twb_calcs.py`, `extract_twb_groups.py`, `tableau_formula_to_seeds.py`.

## Where the workbooks are
`~/Documents/My Tableau Repository/*.twb` (the Nov-2023 family: `Heimdall Nov 2023_Hopscotch.twb` 790 MB is the
source of "Heimdall Demo Slides.pptx"), `/Users/data/*.twb` (Heimdall Demo, Heimdall POI, HeimdallTemplate2022,
ClioPersonas, TabBank*, TabSMBFinal, TabFlowFinal), and the repo's `03_chd_lds_2017-2018/tableau_workbooks/`,
`04_heimdall_tableau_2020-2023/`. `mdfind -name "<deck name>"` finds copies.

## Rules that cost time when ignored
- A .twb is XML but a 700 MB one holds thousands of self-closing `<column .../>` tags. The lazy regex
  `<column\b([^>]*)>(.*?)</column>` is O(n·m) and never finishes — split on `'<column'` and read to the
  next `>` / `</column>` (linear). Stream in 64 MB chunks with a 2–8 MB overlap.
- Read the WHOLE file. `tools/TWB_SEGMENT_DEFINITIONS.md` read only the first 50 MB and therefore lists 7 fields
  for a workbook that has 145; the poles you want (*Hopscotch, _Income, _Average Person, _Ubiquity) sit deep.
- Calculated fields: `<column name='[Calculation_…]' caption='…' role= datatype=><calculation formula='…'/></column>`.
  Keep `name` (other formulas reference it as `[Calculation_…]`) and `caption` (the human name).
- Parameters: `<column … param-domain-type=… value=…>`; the `_Segment` switch formula maps parameter values to
  pole calcs — that is the deck's axis menu.
- Groups/sets = the ROW SOURCES of every chart: `<group name='[_First Names]' caption=…>` with
  `<groupfilter … member='"Aadhya"'/>` per member (quoted strings — strip the quotes; escape `\"`, `\#`).
  Sets named `[Set N]` carry their meaning in `caption` (`Set 12 = _AI Filtered`, `Set 3 = IMDB Combined`).
  Groups with `levels=[none:keyword:nk]` also work. Expect 100k-member groups (Google Ads Placements 126k).
- Row-source filters that are NOT groups: string predicates (`_Websites` = ENDSWITH TLDs, `_Reddit` = startswith
  "r/", `_Movie Filter` = contains " (19"/" (20"), `_Location Based` = near/closest/directions) and keyword_id
  ranges (`_Movie Actors` = id 36000–38000). Recreate those as regexes over the corpus.

## Translating a pole formula
Tableau poles are linear in `zn(avg([anchor]))` terms: nested blocks like
`((zn(avg([a])-0.17)*3 + zn(avg([b])+0.02))/8)*6 - ((zn(avg([c]))+zn(avg([d])))/2)*3 + .042)/(20/3.1)`.
`tableau_formula_to_seeds.py` is a recursive-descent evaluator that folds this into `{anchor: coefficient}`
(+ a constant the axis ignores), normalises max |coef| to 1 and emits engine seeds: `anchor*w`, `-anchor*w`.
It resolves `[Calculation_…]` references recursively; `abs/sqrt/round/iif` mark the result `nonlinear_parts`
(e.g. `_Ubiquity`, `_LDS_Political Intensity`) — those are derived axes, not poles.
Verified anchors from the 2023 workbook: `_Political Spectrum` = 8 right (+) vs 8 left (−), Mother Jones/Newsmax
×2; `*Hopscotch` = 112 anchors; `_Income` = 27; `_Average Person` = single-character searches a b c d e f i l m 3;
`_Ubiquity` = sqrt(volume/avg-person)/493.18; `_*Segment Contrast` = (segment·.22 − avg·.75 − .072)·2;
`_Utahish` = min(Utah, All)/max(All, Utah); `_Volume Visualization` = sqrt(volume/π).
The general form every pole reduces to — score = Σ blocks w·mean(zn(avg([anchor])−c)) — is the same signed,
weighted seed formula Heimdall's `parse_term` grammar expresses; the matched ± pairs (one right outlet against one
left outlet) are what cancel the mainstream factor, and that trick is what the 2026 GADS re-expression plan
(`docs/GADS_FORMULA_TRANSFORM_PLAN.md`) borrows as sibling negatives.

## Outputs to keep
`defs/twb_calcs_raw.json` (all workbooks), `defs/<book>_calcs.md` (readable), `defs/<book>_groups.json` (members,
capped 20k per group), `defs/audiences_from_tableau.json` (seed lists with provenance + original formula).
Grounding of the 2023 groups against today's corpus (2026-09-05): Actors 100%, First Names 99%, IMDB 99%,
INC5000 96%, YouTube 91%, Fake-news 84%, News 76%, Banks 75%, Automotive 59%, Law Landscape 41%, Google
placements 40%, Sports 15% of 15.5k, Influencer handles 23% of 52k.

## Platform blocks
### If you are Claude (Cowork / Claude Code)
Run the extractors on the real Mac (Desktop Commander) with `nohup … &` and a log in `~/clawd/logs/` — a 790 MB
scan takes ~3 min per file; the sandbox cannot see `~/Documents` or `/Users/data`.
### If you are Gemini / Codex
Same scripts via `run_command`; expect the same paths.

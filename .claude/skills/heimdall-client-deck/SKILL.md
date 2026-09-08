---
name: "heimdall-client-deck"
description: "Build a polished, client-facing Heimdall audience deliverable — a Genomic Digital deck (pptx + pdf) in the Fluid/TAB-Bank \"Data Science Insights\" form — from a client's seed vocabulary, with every chart read through a qualitative lens before it ships. Use whenever Ben asks to \"finish the [client] deliverables\", \"make a client presentation/deck for [client]\", turn Heimdall audience work into something a client can see, or redo a Heimdall/Genomic audience study (TAB Bank, Ragnar, Belle Medical style) for any brand — even without the words \"deck\" or \"Heimdall\". Also for \"what did the past Fluid/Heimdall deliverables look like / where are they\"."
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Platform blocks at the end; if yours is missing or a command fails on your toolset, UPDATE THIS SKILL.

# Heimdall client deck — the Genomic Digital audience deliverable

Bundled files at `~/.claude/skills/heimdall-client-deck/` (scripts/deck_data.py, render_charts.py, build_deck.js,
cfgen.sh; templates/*.example.json; references/deliverable-form.md, qualitative-audit.md, speedbumps.md,
chart-audit.example.md). This page is the operating summary. Companion skills, one per building block:
`heimdall-create-audience` (the segment), `heimdall-create-trait` (an axis), `heimdall-add-landscape` (a chart's
rows), `heimdall-full-topic-coverage` (seeds grounded before anything else), `heimdall-competitor-comparison`,
`heimdall-persona-clusters`, `heimdall-poi-landscape`, `heimdall-legacy-scoring-planes` (what to score on when
Matrix h is NaN), `heimdall-2023-deck-recreation` (the 33-chart reference set), `tableau-twb-mining`,
`heimdall-term-disambiguation` (what a seed MEANS before it is a seed), `heimdall-geography-read` (the map, and
the cheapest test that a segment is real), `heimdall-gads-formula-transform` (the plan for re-expressing the
6,161 Google audiences in the 2023 format), `heimdall-insight-prompting` (the copy-generation frame for step 8).

You are producing the thing a prospect or client actually sees: a 40–50 slide deck in the form of the TAB Bank
Data Science Insights deck (Fluid, 2022) — objective → methodology → segment definition → geography → correlation
categories, each a **Big Data Analysis** scatter paired with a **Key Insight** page → personas → competitors →
path forward → appendix — branded Genomic Digital (black / off-white, condensed uppercase headings, one amber
accent, documentary black-and-white photography). Not an internal notebook, not a markdown report.

Ben's standing corrections: "a client presentation, not an internal notebook"; "genomic digital now, not fluid"
(Fluid's *form*, Genomic's *brand*); "not an unqualified script that builds the same things — look at each with a
qualitative lens: does the data make sense, is it similar to these examples, do we have the seeds we need, what can
we substitute". A chart is five stacked decisions — the entity list, row existence and substitution, value
trustworthiness, axes and band, and what the movers say. Do all five on every chart and write them into
`CHART_AUDIT.md`.

## Prior art to open first
`heimdall3.0/00_client_demonstrations/fluid_2020-2022/` — TAB Bank v.F3 PDF (the canonical form; render pp. 12–45
and look), the 87-slide TAB Keynote master, Belle Medical Data Science Insights (site-selection variant), Utah Jazz
proposal, Ragnar Strategy 2021–22. The **2023 demo deck recreated through today's engine**:
`00_client_demonstrations/chart_recreation/out/report.html` — 33 reference charts (social sites, business, websites,
Google audiences/topics, first names, movies, law landscape, actors, banks, family status, paid keywords, sports,
tech providers, handles, news, fake news, POI ×4, auto, YouTube, subreddits, Tab small multiples, finance scatter
matrix, CHD personas) with grades and landmark checks — copy their specs. Brand:
`05_genomic_digital_2024-2026/genomic-digital-overview.pdf`. Worked example: `docs/ragnar_deck/`.

## Reusable axes (already minted, `audience:saved:*-2023`, formulas in `chart_recreation/defs/audience_catalog.json`)
Political Spectrum (16 matched anchors), Income (27), Average Person (single-letter anchors — the baseline every
contrast subtracts), Female Contrast, SMB Owner, Hopscotch SMB-banking persona, Tab Flow / ABL / Existing /
Tabbank.com, Attorney/Law, Mormon Culture, LDS.

**Pick the X-axis, do not default to Political Spectrum** (Ben 2026-09-08: "political spectrum is a great
demo, but not always the best" — the same lesson the 2026-09-06 upgrade note below already learned once for
Ragnar and did not turn into a standing rule). Run `heimdall-comparison-axes`'s menu first: it maps each of
these existing axes (plus Age, Industry Vertical, Competitor/Product/Persona contrasts, and more) to the
client decision it actually answers, and says how to build one that is missing or thin. Political Spectrum
is still the right call when the client's own question is political lean — use it then, and say why.

## Workflow
Mac shell (Desktop Commander) for anything touching the engine or DuckDB; sandbox for matplotlib / pptxgenjs /
LibreOffice QA on the mounted repo. Python: `~/.pyenv/versions/3.13.7/bin/python3.13`. Engine :8000, gateway
:8100, phase1 = `~/github/ammonfife/heimdall3.0/06_scheme_L_2026/phase1`.

0. **Coverage gate.** `POST :8000/api/topic/coverage {"topic": "<client>", "terms": [seeds+entities], "declare": true,
   "queue": true}`. Below ~80% grounded the segment is a hypothesis: queue, declare, schedule a re-check, and say
   so on the methodology slide. Cold seeds ride a serialised lane (one 51-state pull at a time) — never re-queue.
1. **Segment.** Client vocabulary ranked by Google volume; the 3–5 terms with >90% of volume are the core. Check the
   brand word with `POST /api/term_collisions` (`heimdall-term-disambiguation`); subtract competing senses. Seed grammar `term`, `-term`, `term*2`,
   `-term*0.5` (default +2/−1). Publish with `POST /api/audience/define` (saves, declares, queues cold, kicks the
   DURABLE mint) — the older `/api/save_audience` still works but its background mint dies on peer restarts.
   Verify `np.isfinite(m.column("audience:saved:<slug>")).sum() ≈ n_base`.
2. **Geography.** `POST /api/geomap {"audience_terms":[positive seeds]}` → per-state z → `geomap_states.json`. Top
   states must be recognisable or the seeds are wrong — this is the cheapest test that the segment is real
   (`heimdall-geography-read`); do it before any scatter.
3. **Entity lists = landscapes.** 12–14 categories, 30–50 hand-chosen named entities each (expected negatives
   included) → `POST /api/landscape/add` per category (coverage per entity comes back). Substitutes from
   `artifacts/h/[cycle]/rows.json` indexed by first token (never an unindexed LIKE on master_keyword); same
   entity/different surface is fine, different sense is not.
4. **Score on the plane that can answer.** Most named entities (domains, brands) are Matrix ADDENDUM rows and read
   NaN on newly minted poles — `deck_data.py`/`batch_score` will show `h is None`. Score with
   `POST /api/chart/scatter {"rows": {"landscape": ...}, "x": "<axis from heimdall-comparison-axes>", "y": "<segment>", "landmarks": [...]}`
   (`"Political Spectrum (2023)"` is one option among the menu, not the default — see above)
   (state-fingerprint plane, the 2023 statistic) and quote the Matrix agreement r it returns. y = segment score
   (never per-entity "lift" vs Average Person — a popularity axis); average = band of the middle half; exclude by
   name in `exclude.json`: unvolumed outliers, meaning-changing substitutes, zero-volume placeholders.
5. **Qualitative read before rendering.** Landmarks on every chart (5–10 entities with their expected half); a
   GOOD chart has ≥60% in place and r(x,y) ≈ 0.7–0.85 (≥0.95 = the two axes are one thing → Segment Contrast).
   Where the entity read contradicts an earlier anchor read, say so on the slide.
6. **Charts.** `python3 scripts/render_charts.py [deck_dir]` (deck_data.json, geomap_states.json, exclude.json,
   optional disambiguation.json) — or `chart_recreation/recreate_charts.py` specs for the 2023 forms (small
   multiples, scatter matrix, POI, persona clusters). Look at PNGs at full size.
7. **Competitors + personas.** `heimdall-competitor-comparison` (Segment Contrast, profiles, slopes) and
   `heimdall-persona-clusters` pages; personas composed from measured lines PLUS a real demographic read --
   `POST /api/audience_profile {"column": "audience:saved:<slug>", "per_col": 100}` against the segment's own
   Matrix row reads age/income/household/gender straight off the 91 `audience:gads:*` Google demographic
   columns already in the corpus (CHART_AUDIT.md v4, 2026-09-06: this replaced a standing "not scored" caveat
   that was true for one early pass and got copied forward as if it were a platform limit -- it isn't). Only
   write "not measured" on a deck where that call was actually skipped.
8. **Copy + build.** Draft every paragraph through `heimdall-insight-prompting`'s PTCF frame and run its
   grep verification pass before assembling `content.json`. `content_static.json` + `content_categories.json` (per category: chart, note, insight title,
   paragraphs from the named movers with numbers, 6 callouts, 3 negatives) → `content.json`. Photos:
   `scripts/cfgen.sh` (Cloudflare flux-1-schnell; b/w documentary, "absolutely no lettering, no logos"; regenerate
   anything with text; flag as illustration). `node scripts/build_deck.js [deck_dir]`; then pptx-skill QA:
   validate.py, soffice → pdf → pdftoppm contact sheets, look at every slide, `markitdown | grep -i lorem`.
9. **Ship.** Commit deck dir + config + data to heimdall3.0, captains-log, Turso facts for every measurement,
   present pdf + pptx. Anything waiting on Google onboarding gets a scheduled-task rerun, not a "later".

## The numbers every chart must carry (quantitative gates, measured 2026-09-05/06)
- Rows: ≥50% of the landscape found in the corpus, ≥20 rows scored, else the page is a hypothesis. Typical
  grounding: Actors 100%, First Names 99%, INC5000 96%, YouTube 91%, News 76%, Banks 75%, Automotive 59%, Law 41%.
- Landmarks: 5–10 named dots read off the reference chart with their half (`x+y-`); GOOD = ≥60% in place.
- Axis sanity: r(x,y) 0.7–0.85 on Political-Spectrum × segment (the 2023 diagonal); ≥0.95 = one axis, switch Y to
  Segment Contrast (regress Average Person out; on the fp plane the fixed .22/.75 constants give r(contrast,avg)
  = −1.00, so use β = cov/var and print β); ≈0 on Ubiquity × persona.
- Plane agreement: quote r(Matrix h, fingerprint score) on the base rows — 2023 axes run +0.83…+0.89; below 0.7
  the formula did not compose as intended. Never compare two Matrix audience columns raw (shared PC1 = 74.6% of
  variance, r −0.88 with Average Person → any pair r≈0.99).
- Segment distinctness: r(segment, nearest sibling segment) after regressing Average Person < 0.9, else merge or
  sharpen (subtract shared terms). Average Person panel slope must be NEGATIVE in the small multiples.
- Size = Σ Google volume (−1 = never measured → hollow, never size 0); band = middle half of the landscape.

## The reads every chart must survive (qualitative)
- Political Spectrum: Newsmax/Fox right, Mother Jones/MSNBC left — if not, the pole's sign flipped in a compose.
- Persona × POI: national chains (McDonald's, Walmart, Starbucks) LOW, churches / credit unions / independents high.
- Geography: top-5 states recognisable for the segment (Utah for LDS, NYC/CA for fintech); a random map = wrong seeds.
- Substitution: same entity, different surface (`Deutsche Bank` ↔ `deutschebank.com`) is fine and is said on the
  slide; a different sense (`Vanguard` fund vs game) is excluded by name. Zero-volume placeholders drawn hollow
  or excluded, never plotted as movers.
- Drifts since the reference chart are findings, not bugs: name them ("pinterest.com no longer top-right").
- Google audiences appear as member-mean dots (size Σ volume), never as raw Matrix column correlations.

## Speedbumps already solved (references/speedbumps.md + chart_recreation/README.md)
Demo restarts kill long runs (retry loop; peers kickstart freely — post in `.inbox` before you do); `batch_score.in_corpus`
is fingerprint presence, not row presence; `-term` and `term*w` are parsed in `matrix.parse_term`; a compose that
logs `unrecognized arguments` is the fixed argparse bug (idents after `--`); NaN placeholder columns named
`x*0.5` → `scripts/fix_weighted_debris_poles.py`; an all-NaN saved-audience column → `scripts/mint_audience_namespace.py`;
`GET /api/audiences` serves `staging/saved_audiences.json` (republish if it stalls); Keynote export blocked by
iCloud sheet → `keynote-parser` on Index.zip; `artifacts/columns/*.json` gitignored → `git add -f`; zsh eats
`=`-prefixed tokens — quote or use Python.

## Upgrades learned 2026-09-06 (Ragnar v2, review pass via design-critique/validate-data/create-viz)
- **Pre-crop every generated photo to the exact box aspect before placing it.** pptxgenjs's
  `sizing:{type:"cover"}` did NOT reliably preserve aspect ratio when a square (1024x1024)
  Workers-AI photo was placed into a wide title-slide box or a narrow section-strip box —
  it stretched instead of cropping (Ben: "the title is squashed flat/fat, some others are
  squished thin"). Fix, now mandatory: for every (photo, box) pair the deck actually uses,
  pre-crop with PIL to that box's exact w/h aspect ratio (`Image.crop`, center-biased for
  landscape crops, ~35%-from-top-biased for portrait crops of a runner/subject), save as a
  named variant (`<base>_<usage>.png`), and place it with plain width/height and NO `sizing`
  key at all. Also applies to any matplotlib chart PNG placed at a non-matching w/h (the
  disambiguation chart had this same bug independently — its figsize and its slide box did
  not share an aspect ratio; fixed by matching the box to the figure, not the other way
  round). Verify with a one-line script comparing `PIL.Image.open(f).size` aspect against
  every `addImage` call's `w/h` in `build_deck.js` before the first PowerPoint export.
- **Run the client-facing-document-hygiene skill on content.json before the first export,
  not after a complaint.** Ben: "this is a lot of ai slop leaking into the deck." Found on
  the first pass: fabricated first-person customer quotes presented as real voice (a data
  deck inventing quotes reads as fabricated research — describe the persona plainly instead,
  never in quotation marks as if spoken), 109 em-dashes (Ben's standing rule: none, anywhere
  in copy), an aphorism with no agent ("No filter, no veto."), a "·" stat-separator tic, and
  consulting-cliché single-word card titles (ACQUIRE / WARM / REVIVE / AVOID). A blind
  regex em-dash-to-period pass creates its OWN bug — appositives get cut into sentence
  fragments with no verb ("Wasatch Back, Ragnar's own markets." as its own "sentence"). Any
  automated em-dash scrub must require a finite verb in the right-hand clause before ever
  promoting it to a period; default to a comma otherwise.
- **A single-entity "cluster" is not a mean.** If a persona/segment in a matrix chart has
  n=1 member (no averaging happened), say so on the chart and in the callout list, not only
  in the internal audit doc — a client reading only the slide has no way to know a "mean h"
  value is actually one keyword's raw score.
- **Name circular persona selection.** A persona built by picking the most extreme entities
  in an existing category (e.g. "the two most negative correlations in the whole study")
  will, by construction, show an extreme mean — that is not an independent discovery the
  way a persona built from an unrelated category (a hobby list, a competitor list) and found
  to be extreme IS. State which personas were discovered vs. constructed-to-be-extreme; do
  not let both read as equally surprising findings.

## Upgrade learned 2026-09-06, third pass (a permanent aspect-ratio check, not a one-off fix)
- **Write the image/chart aspect check as a script in the deck directory, not a one-time terminal
  command.** The squished-image bug (pptxgenjs stretching a photo or chart PNG that does not share
  its slide box's aspect ratio) recurred a second time in the same session, this time on a newly
  added matplotlib chart whose `figsize` was picked independently of the box it was placed in — proof
  that "I fixed it earlier this session" is not the same as "it cannot recur." `check_image_aspect.py`
  (parses every literal-path `addImage()` call out of `build_deck.js`, opens the corresponding PNG
  with PIL, and fails >2% drift between the image's own pixel aspect and its placed w/h box) is now a
  standing part of the deck's own directory. Run it before every export, including re-exports after a
  content-only change, not only after Ben flags a visual complaint.

## Upgrade learned 2026-09-06, fourth pass (a bar-label collision distinct from the image-stretch bug)
- **A horizontal bar chart's value label can overlap its own row label — this is not the
  squished-image bug, it is a text-layout bug inside the matplotlib figure itself, and
  `check_image_aspect.py` cannot catch it (the PNG's pixel aspect was fine; the collision
  is between two text elements drawn *inside* the image).** Found on the geography chart's
  "Under-index" panel: row category labels (state names) sit, by matplotlib default, on the
  same side of the axis as x=0; when bars are negative they grow *away* from x=0 toward that
  same side, so the longest bars' end-of-bar value labels land directly on top of the row
  label for the most extreme rows (New Jersey's "-1.04" was rendered fused into "New Jersey").
  The over-index panel never showed this because its row labels sit at x=0 and its (positive)
  bars grow *away* from the labels into open space — the two panels were mirror-image layouts
  with only one of them safe by construction.
  **Fix, now the pattern for any diverging/signed horizontal bar chart:** put each panel's row
  labels on the side next to that panel's own x=0 anchor (`ax.yaxis.tick_right()` for a
  negative-only panel), never on the side the bars grow toward. Re-render and eyeball the
  panel with the largest-magnitude bars specifically — a collision only shows up on the
  extreme rows, not the median ones, so a mid-list spot-check will miss it.
- **Read every `kicker` / card-title / callout-label array for length and casing consistency
  before export, not just for content accuracy.** Two real, visible defects survived a full
  content pass: one persona's kicker ("the growth pool nobody is targeting") was 3-4x longer
  than its three siblings ("the buyer", "the repeat participant", "the revival hypothesis"),
  and one card title ("Ironman-brand specialist") was sentence-case among three Title Case
  siblings on the same slide. Neither breaks any script or fails any automated check — they
  only show up as a felt inconsistency when the slide is looked at next to its neighbors.
  Check by grepping content.json for each array of sibling labels (`personas[].kicker`,
  each `strategy_pages[].cards[][0]`, `persona_matrix_callouts[][0]`) and confirming the same
  word count and letter-casing convention holds across every entry in that array — and prefer
  reusing a phrase already established elsewhere in the deck's own copy (the fixed persona
  kicker reused "growth pool" from `persona_section_blurb`, which already used the term)
  over inventing a new short label.

## Upgrade learned 2026-09-06, fifth pass (a chart grammar borrowed from another client's audience)

`render_charts.py`'s category scatter used political spectrum as the x-axis on all 13
category pages, inherited from the TAB Bank chart grammar, where political lean was a real
segmentation signal for a financial-services audience. Ben caught it after the deck was
already through a full self-review pass: for Ragnar (a race/relay brand) it made no sense on
12 of 13 pages — shoe brands, food chains, movies plotted on a "leans left / leans right"
spectrum — and directly contradicted the deck's own finding that the audience is
"politically ordinary." His framing: not a blanket rule against political data, just wrong
for this deck's audience and category set. Fix was to swap the axis to a dimension already
computed for every point (US search volume, log scale) rather than invent a new one.

Standing QA habit: when a chart type is reused from a prior client's deliverable, check
every axis against the NEW client's actual audience and category list, not just against
whether the code still runs without error. A borrowed chart grammar carries the prior
client's segmentation assumptions with it — an axis that was load-bearing for one audience
can be dead weight or actively wrong for another. Grep the chart-rendering script for any
axis/label defined in a comment referencing a different client name and re-justify it for
the current one before shipping.

## Upgrade learned 2026-09-06, sixth pass (a formula reweight ripples the whole corpus, not just the target)

Ben asked for the audience's own subject terms (ragnar races/relay/trail) to score 0.90–1.00
against their own audience column, "avoids weird questions." Correction mid-request: do this
by re-weighting the seed terms IN the audience formula itself (`ragnar races*5`, `ragnar
relay*4`, `ragnar trail*5.3` via `heimdall_core.matrix.compose_and_persist(terms, name=...)`),
never as a display-layer rescale of already-computed h — a rescale was tried first and
explicitly rejected ("i mean rescaling IN the audience actual formula/weights, not post H").

Gotcha: `scripts/mint_audience_namespace.py`'s `missing = [t for t in todo if t[0] not in have
or t[0] in _nan_cols]` skip logic never recomposes an audience whose column NAME already
exists, even when the underlying seed weights changed. A plain `/api/audience/define`
redefinition silently no-ops. Bypass by calling `matrix.compose_and_persist()` directly against
the audience's slug; iterate the weights (three tries here) and re-check with `/api/batch_score`
each time, since the mapping from weight to resulting h is not simply proportional (cross-terms
in the composition move together).

The real cost: reweighting three terms shifted the WHOLE audience vector, which changed every
h in the corpus by a small amount — enough that dozens of entities crossed zero (Chewy, hunting,
sourdough, Ford F-150/Bronco/Tacoma, Denver Broncos, Fox News, Netflix, Game of Thrones,
Yellowstone, Starlink, Vikings, Ironman). Ironman going from "the one clean negative in the
study" to inside the average band broke three separate strategic claims built on the old read
(a persona-matrix card, a strategy-page "four plays" card, a creative-hooks line) — none of
which mention the reweighted terms directly, so a scoped re-check of only the category charts
would have missed them. Standing habit: after ANY audience formula change, re-derive every
`insight`/persona/strategy sentence that cites a specific entity's sign or rank, not only the
category the reweight targeted — grep the deck's content file for named entities against the
freshly regenerated data and diff, rather than trusting the old prose still describes the new
numbers.

## Upgrade learned 2026-09-06, seventh pass (a bare operand isn't a column; verify a toggle at the endpoint, not the launchd label)

Building a bipolar trait from raw high-volume terms (`-ironman`, `-marathon`) as direct
`compose_and_persist` operands silently drops them: `audience_columns()` only resolves
operands that are already MINTED columns, and a common single word with real search volume
is often just a corpus ROW, never independently minted as its own pole. Fix: define it as a
one-line audience first (`/api/audience/define` with a handful of matched seeds) — that mints
a column — then compose the TRAIT as a contrast of two audience columns
(`-audience:saved:solo-x`, `audience:saved:team-y`), not a flat mixed list of raw terms and
signs. This is the same shape as the 2023 "Segment Contrast" pattern in
`heimdall-competitor-comparison` — a trait built from real anchors is often better expressed
as (population A) − (population B) than as a hand-tuned sign list.

Second lesson: deepening a thin audience (2–3 terms) is not the same task as verifying it's
grounded. `Hood to Coast customer` had 3 seeds; 2 of the 3 ("hood to coast relay", "hood to
coast route") had never grounded and were silently contributing nothing since the column was
first minted — a `topic/coverage` check the pre-existing terms would have caught this on day
one. Run coverage on the CURRENT seeds of an audience you're "deepening", not just on the new
candidates you're adding.

Third: when a `llmctl` toggle or similar on/off switch matters to whether a step can proceed,
check the endpoint itself (`curl localhost:1234/v1/models`, `lms status`), not just the
control's own status output. `llmctl status` reporting `mode: on` with all launchd jobs
"loaded" was not sufficient — the LM Studio app process was up but its API **server** was
off (`lms server start` reported `Server: OFF`), so the embedding endpoint Heimdall calls was
unreachable despite every toggle saying "on". A control's status is a claim about what it
last did, not a live measurement of the thing you actually need.

## Platform blocks
### If you are Claude (Cowork / Claude Code)
Desktop Commander for engine/DuckDB/Keynote; sandbox bash for pptxgenjs/LibreOffice on the mounted repo.
### If you are Gemini / Codex
Same routes and scripts via `run_command`; no AppleScript — LibreOffice for exports.

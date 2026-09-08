---
name: heimdall-persona-clusters
description: Build a persona study in Heimdall the CHD/CSC way — personas as keyword CLUSTERS placed on two trait axes (e.g. Contrast Rising-Generation-vs-General-Membership × Risk-of-Leaving), dot = cluster mean, size = Σ volume, colored by "original hypothesis" vs "reality" — from methodology decks, dimension definitions, or a client's persona list. Use when Ben asks for personas, "which persona is at risk", "recreate PersonasCHD", a cluster analysis, or a persona page for a deck.
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset, UPDATE THIS SKILL with an `If you are [Platform]` block.

# Persona clusters on trait axes (the PersonasCHD form)

The 2017-18 CHD chart: X = corr(Rising Generation) − corr(General Membership), Y = Risk of Leaving
(= mean correlation with "Losing Faith – General" and "Disaffected with LDS Church"), one dot per persona
(Active-ly Conflicted, Willing to Ask Tough Questions, Investigator/Pre-Testimony, That's News to Me, Fact Checking,
Lots of Small Questions, Mormon Corridor, Mormon Fan Club, Yeah I Already Knew That, Confirming not Challenging,
What Does the Manual Say?, Deseret Book Platinum), size = volume, two panels: Original Hypothesis vs Reality.
Definitions live in `00_client_demonstrations/chart_recreation/defs/audience_catalog.json` (`role: persona|trait|
segment`, each with `basis` quoting the slide) and the chart spec `35_chd_personas` in `chart_specs.py`.

## Anatomy
- Two SEGMENTS to contrast (X): populations at two life stages / tiers (`heimdall-create-audience`).
- One or two RISK/ATTRIBUTE traits (Y): `heimdall-create-trait`; pool thin ones (Losing Faith ∪ Disaffected).
- N PERSONAS: each a keyword cluster of 8–15 seeds in ONE register (the 9 CSC dimensions — Belief in Institution,
  Church Attendance, Core Doctrine, Cultural Doctrine, Diligence, Conformity, LDS Culture, Progressive, Tough
  Questions — are traits; personas are the clusters those traits carve out).
- Filters the original applied: exclude pharma / census datasets, a relevance flag, an investigator/outsider flag
  (socialCHD.twb groups) — recreate as landscapes and exclude lists.

## Procedure
1. Coverage first (`heimdall-full-topic-coverage`): the CHD vocabulary grounded 2/225 on 2026-09-05 — a persona
   chart on 4 anchors is a hypothesis, label it so. Declare + queue, schedule the re-run.
2. Define segments and traits via `/api/audience/define` and `/api/trait/create`; personas as catalog entries
   (`role: persona`), NOT as poles.
3. Score each persona's members on the fingerprint plane (`recreate_charts.run_chd`): x = mean(seg_A − seg_B),
   y = mean(risk), v = Σ volume; report members found per persona.
4. Landmarks from the methodology: high-risk in 2018 = Lots of Small Questions, Mormon Corridor, What Does the
   Manual Say?; low-risk = Investigator/Pre-Testimony, Deseret Book Platinum; "Mormon Fan Club and Corridor are at
   greater risk"; "members with markers of being active are at much more risk when presented with new /
   conflicting / troubling information" (PRESENTATION_012518 slides 44-47). Reality vs hypothesis = two color
   groupings of the same dots.
5. Deck copy: one line per persona from its members' numbers (draft through `heimdall-insight-prompting`'s
   Persona-narrative writer Gem); the life-stage read (Young / Mission / College /
   Parenting / Retired) as a second chart if age traits exist.

## Upgrade learned 2026-09-06 (Ragnar persona matrix, review pass via data:validate-data)
- **Flag n=1 clusters as single entities, not means**, on the chart itself (label + a
  distinct legend note), not only in an audit doc. `validate-data`'s "average of averages"
  and small-sample pitfalls both apply: a one-member "cluster" carries no averaging and
  should not visually compete on equal footing (same dot style, same "mean h=" label) with
  an 8-member cluster without saying so.
- **Distinguish a discovered persona from a constructed-extreme persona.** Building a
  persona FROM the tails of an already-scored category (the two most negative rows in the
  whole study) will, by construction, score as extreme — that's a valid revival/exclusion
  hypothesis but not an independent finding. A persona built from an unrelated category
  (a hobby list scored against a segment it was never selected to match) and found to be
  extreme IS an independent finding. State which is which; do not let a mechanically-extreme
  cluster read with the same "the data surprised us" framing as a genuinely discovered one.
- **When crowding overlaps chart labels** (several cluster means sit within a narrow x-range),
  do not rely on auto text placement — assign each label a manual offset so none overlaps a
  neighboring dot's own annotation (`design-critique` legibility check). Six or fewer
  clusters is small enough to hand-place; `adjustText` (already used for the 40+ entity
  scatters) is unnecessary at this scale and can still produce a bad first layout.

## Upgrade learned 2026-09-06, second pass (axis choice and rasterized-chart QA)
- **The Y axis (or any counteraxis) is a strategic choice, not a default.** Political spectrum
  is a fine axis when the deliverable is testing whether political targeting matters (a real,
  citable null result). It is a weak default for a persona matrix meant to guide spend, because
  it rarely maps to a lever the client can pull. Run `heimdall-comparison-axes`'s menu (income,
  age, industry vertical, urban/rural, gender, competitor/product/persona contrasts and more,
  each mapped to what client decision it answers and what already exists to serve it) before
  picking one, rather than reaching for whichever axis was used last. Pick from already-existing
  saved audience/trait columns before minting anything new, and say in the deck why that axis was
  chosen over the obvious default.
- **Hand-placed label offsets must be checked against the actual rendered coordinates, not
  estimated from memory.** A first attempt at manual offsets, sized only by eyeballing which
  clusters "seemed close," produced worse overlap than the auto-placement it replaced, because
  the estimated dot positions were wrong. The fix: print the real (x, y) for every cluster,
  compute label landing zones from those numbers and the actual point-to-data-unit scale, then
  re-render and read the PNG at full size before trusting it — twice, in this case, since the
  first corrected layout still had one label landing on top of a different cluster's dot.
- **A chart is an image, not text — grep-based hygiene checks (em-dash counts, etc.) only see
  the PDF's extractable text layer and will pass a chart with a dash baked into its own
  rasterized labels.** Any text drawn by matplotlib/PIL/etc. into a chart needs the same
  hygiene pass applied to its own label strings, and needs a visual screenshot check, not just
  a text-layer grep, before the chart is considered clean.

## Platform blocks
### If you are Claude (Cowork / Claude Code)
`~/.pyenv/versions/3.13.7/bin/python3.13 recreate_charts.py --only 35_chd_personas` on the real Mac; engine :8000.
### If you are Gemini / Codex
Same script via `run_command`.

# The deliverable form — TAB Bank Data Science Insights (Fluid, 2022), page by page

Source: `00_client_demonstrations/fluid_2020-2022/TAB Bank Data Science Final Deliverable v.F3.pdf`
(81 pp). Render pages to images (`pdftoppm -r 40`) and make contact sheets; do not work from
memory of it.

## Spine (and the Genomic Digital slide that replaces each)

| TAB page(s) | what it is | our slide |
|---|---|---|
| 1 | cover: client · DATA SCIENCE INSIGHTS · market | `cover()` — full-bleed b/w photo, amber kicker, condensed title |
| 2 | Project Objective, half-bleed photo | objective + van/photo right |
| 3 | contents (Methodology / Customer / Broker / Path forward) | CONTENTS with 01–04 |
| 4–9 | Methodology: 4 steps (identify segment → digital fingerprint → billions of correlations → isolate insights), one page each with a chart | METHODOLOGY 4-column + dark "RUN BILLIONS OF CORRELATIONS" stat page |
| 10 | Strengths / Limitations (assumption free · reliable data · statistically derived / art+science · segment dependent · search based) | same structure, our three each |
| 11 | section divider with persona photo | `section()` |
| 12 | Segment Definition — the literal formula, `zn(avg([term]))` lines with signs | formula block in Courier, negatives in amber |
| 13 | "13 PRIMARY CORRELATION CATEGORIES" numbered grid | same, ours 12–14 |
| 14–45 | per category: **Big Data Analysis** scatter page (title left, chart right, one-line data note) then **Key Insight** page (headline, 2–3 paragraphs with numbers, logo grid / photo) | same pair; our Key Insight carries a "STRONGEST SIGNALS" list with values and a "NOT THIS AUDIENCE" list |
| 46 / 79 | persona: "Meet Aaron / Meet Troy" — photo, quote, bullets | `personas[]` |
| 47–49 / 80–82 | Strategic implications: value proposition, creative, optimizations/channels | 4 strategy pages with cards |
| 83–87 | appendix ("stuff that wasn't good enough for prime time") | how-to-read + provenance |

## The scatter grammar (p. 33 "Sports Affinities" is the clearest example)

- **y** = correlation of the entity with the segment pole (TAB: "Tab ABL Customer Persona"; ours: `h(row, audience:saved:<slug>)`).
- **x** = a contrast axis; TAB used `_Political Spectrum` on every category. Ours: `h(row, republican) − h(row, democrat)`. It doubles as a sanity check — hunting/NASCAR right, yoga/Premier League left.
- **size** = search volume (log).
- **grey bands**: horizontal "Average" band on y; vertical neutral band on x.
- **labels**: every point labelled with the entity as searched (TAB used Tableau; we use matplotlib + adjustText, amber for the top five, dark grey for the bottom three).
- **data note** under the title says where the list came from ("generated from lists of the most popular sports leagues and teams globally").

## What the Key Insight page does

It names entities and gives numbers ("FreedomWorks +.62, Rush Limbaugh +.556, FoxNews +.53"),
states the negative side ("Center for American Progress −.551"), and draws one strategic line
("Conservative Republicans"). It never summarises the aggregate. When a finding is null (Ragnar
politics) or contradicts a prior read (the van), the page says so plainly — that is what makes
the rest credible.

## Belle Medical variant (Nov 2021)

`Belle Medical_Fluid vFinal (2).pptx` — industry trend by keyword-cluster correlation, competitor
correlation with a macro series (IRS stimulus r² .84), geography of customer segments vs
uncorrelated demand, **intersection-level site selection**, keyword arbitrage, platform
prioritisation "with Heimdall". Use when the client question is *where to open* rather than
*who to buy*.

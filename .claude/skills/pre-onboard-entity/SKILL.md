---
name: pre-onboard-entity
description: Fully onboard a company, product, event, brand, candidate, or organization into Heimdall — enumerate senses, cross with axes, map competitors and ICPs, crawl the site, register anchors, and verify they resolved. Use when taking on a new client or analyzing a new entity, or when the user says "pre-onboard", "onboard <brand>", "new client", "set up <company>", or asks what keywords or audiences a brand needs.
---

# Pre-onboard an entity

Turns a bare entity name into a **built, verified** Heimdall footprint.

An audience column is the present-only mean of its **member columns**. A member with no
column contributes nothing. So an onboarding that produces taxonomy without anchors
produces a plausible-looking column built from whatever happened to already exist — a
silent failure. Every step below therefore carries a **proof**, and the skill is not
finished until all of them pass.

---

## DEFINITION OF DONE

The skill is finished when **all eight outcomes hold and each proof passes**. Anything less
is a partial run and must be reported as such, with the failing proof named.

| # | OUTCOME | DELIVERABLE | PROOF (how you know) |
|---|---|---|---|
| 1 | Every sense of the entity name is enumerated, including irrelevant ones | sense node list in the worked-example doc | for each sense, a probe result showing whether any competing sense is **already an anchor**; if one is, the collision is live |
| 2 | Each sense is crossed with the axes it genuinely has | sense×axis matrix with per-cell seeds | every filled cell has ≥3 seeds matching that axis's register; every empty cell has a one-line reason |
| 3 | Competitors are split direct vs adjacent | competitor table with `child`/`related` per row | no competitor is unlabelled; `related` used wherever the category differs |
| 4 | ICPs named, with gaps declared | ICP table | every ICP either resolves to a real node or is explicitly marked "no axis exists" |
| 5 | Site vocabulary ingested | crawl log | `crawl_site_onboard.py` reports pages onboarded > 0 and each `corpus_coverage` body is non-empty (**HTTP 200 is not proof**) |
| 6 | Curated anchors registered | anchor list, tiered | `/api/register_keywords` returns `registered + already_present == len(requested)` |
| 7 | Anchors actually resolved into the corpus | verification output | a re-probe shows the terms present as rows **and** `/api/lookup` returns a score, not `queued: true` |
| 8 | Findings recorded | `WORKED_EXAMPLE_<ENTITY>.md` + Turso todos | doc committed; every gap discovered has a todo |

**Report format at the end:** one line per outcome, `DONE <evidence>` or `PARTIAL <what
failed, what is next>`. Never report an outcome as done on the strength of a status code.

---

## SUB-SKILLS

Build these as separate skills when this one is next run; today they are inline steps.

| sub-skill | why it separates | status |
|---|---|---|
| `crawl-site-vocabulary` | reusable beyond onboarding (competitor sites, content audits); has its own failure modes (robots, sitemaps, JS-rendered pages) | **script exists**: `scripts/crawl_site_onboard.py`; not yet a skill |
| `disambiguate-senses` | needed any time a token is ambiguous, not just at onboarding; the invariant work is subtle enough to deserve its own doc | **not built** |
| `classify-axis` | applying `AUDIENCE_AXIS_REGISTER.md` to a seed set is a judgement task that recurs on every audience edit | **not built** |
| `verify-anchors-landed` | the honest-verification half; reusable by any onboarding or backfill | **not built** |

---

## APIv2 (`/v1` gateway) — what must be created or updated

Measured against the live gateway. The demo (`:8000`) has most of this; the **product API
does not**, so a client-facing onboarding cannot be driven through `/v1` today.

| step | needs | `/v1` today | action |
|---|---|---|---|
| sense collision probe | is term X a row? an anchor? | — | **CREATE** `/v1/term_status` → `{row, anchor, senses[]}` |
| crawl a site | discover + onboard N pages | `/v1/onboard` (single URL only) | **UPDATE** `/v1/onboard` to accept `{site, max_pages}`, or **CREATE** `/v1/crawl_onboard` |
| bulk anchor registration | register a keyword list, no quota spend | — (demo-only `/api/register_keywords`) | **CREATE** `/v1/register_keywords` |
| hierarchy / tag lookup | where does a node sit, what tags it | — | **CREATE** `/v1/hierarchy/{node}` and `/v1/tags` (blocked on `column_tags`, todo #13266) |
| verify a term resolved | score vs still queued | `/v1/lookup` | OK — but callers must distinguish `queued:true` from a score |
| create the audiences | persist composed audiences | `/v1/audiences` POST | OK |
| score / compare | validate the result | `/v1/score`, `/v1/compare_audiences` | OK |

Four creates, one update. Until then, run steps 1/5/6 against the demo on `:8000` and note
in the report that the client-facing path is incomplete.

---

## STEPS

### 1. Enumerate SENSES — never assume one

One string is usually several populations: `Ragnar` is the race, the company, the employer,
Ragnar Lothbrok, **and** Ragnar Anton Kittil Frisch the Norwegian economist. Create a node
per sense **including irrelevant ones**, so they can be named and EXCLUDED.

```bash
cd 06_scheme_L_2026/phase1 && python3 - <<'PY'
import json; from pathlib import Path
cyc=sorted(p for p in Path('artifacts/h').iterdir() if p.is_dir())[-1]
m=json.loads((cyc/'manifest.json').read_text())
rows={str(r).strip().lower() for r in json.loads((cyc/m['rows_file']).read_text())}
tok={str(c).strip().lower() for c in json.loads((cyc/m['tokens_cols_file']).read_text())}
for t in ['<entity>','<rival sense term>']:
    print(f"{t:32} row={t in rows}  ANCHOR={t in tok}")
PY
```

**PROOF:** if a competing sense is already an anchor, the collision is live and will
corrupt the audience. (Real case: `vikings` was an anchor, `ragnar` was not.)

### 2. Cross each sense with the AXES

The sense says *which* entity; the axis says *what relationship*. Independent dimensions.

| axis | population | seed register |
|---|---|---|
| topic | researching what it is | `what is X`, `how does X work`, `X rules` |
| interest | aware, considering | `X locations`, `X reviews`, `X vs Y` |
| affinity | identifies with it, repeat | loyalty tiers, own domain, sub-brands, community |
| in-market | about to buy | `register/buy/price/discount/dates/near me` |
| role | organiser, decision maker | `how to organize X`, `X captain`, `X coordinator` |
| firmographic | as an employer | `jobs at X`, `X careers`, `X glassdoor` |

**Empty cells are findings** — nobody registers for a saga. Detail:
`AUDIENCE_AXIS_REGISTER.md`.

### 3. Competitors — `child` vs `related`

`child` = same category. `related` = same customer, different category. That distinction
*is* the competitive analysis. Include rivals for the same budget and calendar slot.

### 4. ICPs, traits, geo

ICPs: who buys; name where no axis exists. Traits (team size, duration, seasonality)
describe the *product*, not a population — **column metadata, not tags**. Geo: home market
plus every operating market.

### 5. CRAWL THE SITE — not just the landing page

A landing page is the least representative page a brand has; it is positioning copy. Race
pages carry event names, FAQ carries prospect questions, blog carries participant register.

```bash
python3 scripts/crawl_site_onboard.py <site> --dry-run --max-pages 150   # discover
python3 scripts/crawl_site_onboard.py <site> --max-pages 150             # onboard
```

Discovery unions three rungs because none is reliable — measured on runragnar.com,
robots.txt advertises `sitemap-index.xml` and that URL **404s**; link-crawl carried it.

**PROOF:** pages onboarded > 0 and bodies report real decomposition.

### 6. Emit and register the ANCHORS

Direction B (node → columns) IS the onboarding plan. Tier them: brand+senses, category,
competitors, affinity, in-market, role. Expect 40–60.

```bash
curl -s -X POST http://127.0.0.1:8000/api/register_keywords \
  -H 'Content-Type: application/json' \
  -d '{"keywords":[...],"source":"pre-onboard:<entity>-<date>"}'
```

Bulk registration at `status='new'`, **no quota spend**; the existing pipeline resolves them.
Use `/api/onboard` only for prose or a URL.

**PROOF:** `registered + already_present == requested`.

### 7. VERIFY they resolved — the step that is always skipped

```bash
curl -s -X POST http://127.0.0.1:8000/api/lookup -H 'Content-Type: application/json' \
  -d '{"keyword":"<a term the site uses>"}'
```

`queued:true, building:true` means **not done**. Re-run the step-1 probe and report
landed-vs-requested as a number.

### 8. Record

Write `WORKED_EXAMPLE_<ENTITY>.md`; file a Turso todo for every gap.

---

## HARD RULES

- **Never tag a bare ambiguous token as `child`.** It is a subset of no sense. Use `related`.
- **The subset invariant is per link type.** `child` = column ⊆ node; `parent` = node and
  its whole subtree apply; `alias` = same population; `related` = neither contains.
- **Choose the axis before writing seeds.** Seeds spanning two registers mean **two
  audiences**, not one badly-filed one.
- **Do not invent nodes.** Check every target against the live tree; report gaps as gaps.
- **Do not mint a column for a pure reference.** All-`audience:gads:*` seeds = an `alias`
  link, not a new audience.
- **HTTP 200 is never proof.** Assert bodies, then re-read state.

Reference implementation: `WORKED_EXAMPLE_RAGNAR.md`.

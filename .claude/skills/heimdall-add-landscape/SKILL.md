---
name: heimdall-add-landscape
description: Add a LANDSCAPE to Heimdall — a named list of entities (banks, law firms, social sites, sports teams, YouTube channels, fintech domains, a client's competitors…) that becomes the row source of a category chart — with per-entity coverage, onboarding of the cold ones, and a landmark-checked scatter. Use when Ben says "add a landscape", "build the <category> chart", "which of these <entities> does the engine know", or a client deck needs a new Big Data Analysis category.
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset, UPDATE THIS SKILL with an `If you are [Platform]` block.

# Adding a landscape (the rows of a chart)

Routes (routes/legacy_charts.py, engine :8000):
- `POST /api/landscape/add {"name", "terms": [...], "source", "note", "queue": true}` → stores
  `staging/landscapes/<slug>.json` with per-term `grounded / in_fingerprint / volume / no_volume`, queues cold terms.
- `GET /api/landscapes`, `GET /api/landscape/<name>`.
- `POST /api/chart/scatter {"rows": {"landscape": "<name>"}, "x": ..., "y": ..., "landmarks": [...]}`.
Bulk example: `00_client_demonstrations/chart_recreation/register_landscapes.py` registers the 23 landscapes of
the Nov-2023 deck straight from the Tableau groups.

## Where entity lists come from (best first)
1. The client's own list (customers, competitors, referral sites) — the deck's "landscape" pages.
2. A Tableau group from the legacy workbooks (`defs/nov2023_groups.json`: INC 5000 19.6k, First Names 3.4k, IMDB
   3.4k, Actors 2.5k, YouTube channels 2.5k, Banks 753, News outlets 269, Fake-news 82, Law Landscape 227,
   Automotive 257, Tab Website/Flow landscapes, Digital Marketing landscape, Job Titles, Russell 2000, Stock tickers).
3. A regex over the corpus (`{"regex": r"\.(com|net|org)$", "min_volume": 200000, "top": 400}` gives "Websites";
   `r"^/?r/"` gives subreddits; legal-software phrases by `(law|legal|attorney).*(software|billing)`).
4. The engine's own Google audiences (`{"gads": "user_interest"|"topic_constant"}`) or POIs (`{"poi": true}`).
Names must be SEARCH TERMS. Ad headlines ("#1 Attorney Billing Software") ground at 0.4%; Title-Case Google
taxonomy labels ("Trips to Cuba") at 12% — substitute real phrases or use the gads columns.

## Coverage is the first read
Measured 2026-09-05 (1,500-term samples): Actors 100%, First Names 99%, IMDB top 99%, INC5000 96%, YouTube 91%,
Gendered phrases 98%, Fake-news 84%, News 76%, Banks 75%, Automotive 59%, Law Landscape 41%, Google placements
40%, Sports 15% of 15.5k (top-400 by volume is the chart), Influencer handles 23% of 52k.
`POST /api/topic/coverage {"landscape": "<name>"}` adds `matrix_row base|addendum` and `is_column` — most
domain-style entities are ADDENDUM rows (92.5% of the social sites), which is why charts score on the
fingerprint plane and report Matrix agreement.

## Substitution rules (Ben: "what can we substitute")
Same entity, different surface (`Deutsche Bank` ↔ `deutschebank.com`, `LINKEDIN` ↔ `linkedin.com`) is fine —
say which surface plotted. A different SENSE (`Vanguard` the fund vs the game) is not. Drop zero-volume
placeholder names by name in an exclude list; keep plausible unvolumed rows drawn hollow.

## Then chart it and look
Landmarks = 5–10 dots read off the reference chart with their half (`"x+y-"`). GOOD needs ≥50% rows found,
≥20 scored, ≥60% landmarks in the expected half; r(x,y) on Political-Spectrum × persona charts is ~+0.7–0.85 —
much higher means the two axes are the same thing. Write drifts on the chart ("pinterest.com is no longer
top-right"). PNGs: `recreate_charts.py` with a chart_specs entry; the API returns points + checks only.

## Platform blocks
### If you are Claude (Cowork / Claude Code)
Real Mac shell for the engine calls; the 126k Google-placements group takes ~26 status batches — run bulk
registrations with `nohup … > ~/clawd/logs/<name>.log &`.
### If you are Gemini / Codex
Same routes via `run_command`.

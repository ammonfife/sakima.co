# The qualitative lens — five levels under every "simple" chart

Ben, 2026-09-05: "does the data make sense, is it similar to these examples, do we have the
seeds we need, what can we substitute if needed. do you understand the multiple levels that go
into a 'simple' chart". Answer all five for every category and write the answers into
`CHART_AUDIT.md` (one row per chart: makes sense? / like the example? / seeds & substitutions /
verdict). `references/chart-audit.example.md` is the Ragnar one.

## Level 1 — the list
Named entities, chosen by hand for THIS client and category, 30–50 per category. Leagues and
teams (national + the client's home markets), brands, chains, destinations, titles, outlets.
Include what you expect to be negative as well as positive — the under-index is half the story
(TAB: Tesla negative, Ford positive). A list that only contains the client's own world charts
as a blob.

## Level 2 — does each entity exist as a corpus row?
`deck_data.py` prints `missing [...]` per category. For each missing entity search
`rows.json` for a real phrase that means the same thing (`the north face`, `alltrails com`,
`triathlon training plan`). Reject substitutes that change the meaning — `apple pay wallet`,
`ring doorbell camera price`, `chariots of fire song`, `college football live` — a
streaming-intent or shopping-intent variant is a different population. Entities with no row
are queued for onboarding by the engine automatically; note them for the next cycle.

Watch the `/api/batch_score` fields: `in_corpus` reports the geo *fingerprint*, not row
membership — a keyword can have `in_corpus: false` and a valid `h`. Chart on `h is not None`.

## Level 3 — is the value trustworthy?
- **Volume None/0 with a large |h|** → almost always an unvolumed variant of a real row
  (`new york times` +0.136, `nest thermostat` +0.119) — drop by name.
- **Volume 0 with h≈0** on a famous name (`donald trump`, `joe biden`) → placeholder row, not
  a measurement — drop.
- **Volume None but plausible** (Tesla Model Y, Oura) → keep; say so in the audit.
- **A value that contradicts an earlier anchor-level finding** → do not smooth it. Check the
  population behind the phrase (who searches "15 passenger van rental"? church groups and big
  families) and report the correction on the slide.

## Level 4 — the axes and the band
- y = the segment correlation itself. Do **not** subtract an "average person" pole per entity:
  a 20-generic-row control is a popularity axis and punishes every high-volume brand
  (creatine seg +0.000, "lift" −0.315). Draw the average as a band = the middle half of all
  charted entities, as TAB drew it.
- x = republican − democrat columns. Read it as a sanity check on every chart before trusting y.
- Magnitudes are small (a relay race is a small population, |h| ≤ 0.16); say "read sign,
  ordering and distance from the band, not the decimal" in Limitations.

## Level 5 — what do the movers say?
Write the insight from the named entities above and below the band, with numbers. Look for
the second-order pattern: Hydro Flask + / Yeti − (Yeti's audience is hunting and trucks,
both negative elsewhere); Nuun + / Body Armor − (endurance nutrition vs sports drink);
mortgage rates + / pregnancy − (a life stage, not a demographic). If a category has no
movers, that is the finding (politics) — chart it and say it.

## Verdicts
SHIP · SHIP with correction stated · SHIP, thinnest (name what would thicken it) · MERGE into
another category · DROP. A category with fewer than ~15 trustworthy entities is merged or
dropped, never padded.

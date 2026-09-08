---
name: heimdall-comparison-axes
description: "The menu of comparison axes (political, income, age, industry vertical, competitor-vs-competitor, product-vs-product, persona-vs-persona, and more) a Heimdall deck, persona matrix, or competitor page can be built on, plus the decision rule for picking one and the build path for one that is missing or thin. Use before choosing an X-axis in heimdall-client-deck step 4, a Y-axis/counteraxis in heimdall-persona-clusters, or what to contrast in heimdall-competitor-comparison -- and any time a deck is defaulting to Political Spectrum without having asked whether it is the right axis for this client."
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset, UPDATE THIS SKILL with an `If you are [Platform]` block.

# Heimdall comparison axes (pick the axis, don't default to it)

Companion to `heimdall-client-deck` (step 4's X-axis choice), `heimdall-persona-clusters` (the Y-axis /
counteraxis choice, its own "axis is a strategic choice, not a default" note added 2026-09-06), and
`heimdall-competitor-comparison` (what two things get contrasted). Political Spectrum is a great demo -- 16
matched anchors, r(Matrix h, plane) +0.893, the house chart since the 2023 deck -- but Ben (2026-09-08): "not
always the best." This skill is the fix: a menu of axis TYPES, what each is actually good for, what already
exists to serve it, and how to build one that does not exist yet. It does not replace a single default with a
different single default -- it replaces defaulting with picking.

## The rule

**Choose the axis type before touching the data, and tie it to a decision the client can actually make.**
Political Spectrum answers "does political lean predict behavior here" -- a real, citable question, but only
the right one when THAT is the client's question. A pricing client needs Income. A B2B client needs Industry
Vertical or a Persona split (buyer vs. user). A two-brand pitch needs Competitor-vs-Competitor. Say in the deck
(or the methodology note) which axis was chosen and why it, not the house default, answers this client's
question -- `heimdall-persona-clusters` already requires this for its own axis choice; this skill extends the
same requirement to `heimdall-client-deck` and `heimdall-competitor-comparison`.

## Two different mechanisms, one menu

Heimdall has two distinct ways to place a comparison, and which one an axis uses determines how you build it:

- **Fixed X-axis anchor (state-fingerprint Plane 1, `heimdall-legacy-scoring-planes`)**: a named, pre-scored
  formula like `audience:saved:political-spectrum-2023` that any landscape's rows get plotted against. This is
  what `heimdall-client-deck` step 4's `"x": "..."` parameter takes. Political Spectrum, Income, SMB Owner,
  Hopscotch, Tab Flow/ABL/Existing/Tabbank.com, Attorney/Law, Mormon Culture, LDS, Female Contrast and Average
  Person are the existing ones -- nothing about Plane 1 is political-spectrum-specific, it scores ANY signed,
  weighted anchor set the same way (`Zn @ A.T @ w`). A new axis here is a new anchor formula, built and scored
  exactly like the 2023 originals were.
- **Segment Contrast (two live segments, `heimdall-competitor-comparison`)**: `c = s - β·avg` on the SAME plane,
  comparing one built segment directly against another (or against Average Person) instead of against a fixed
  named axis. This is the mechanism for anything inherently client-specific -- a named competitor, a named
  product, a named persona pair -- because those have no business being a permanent, reusable, named axis in
  the first place.

Rule of thumb: if the axis should exist for every future client (a population dimension like income or age),
build it as a Plane-1 anchor. If the axis only makes sense for THIS client (their competitor, their two
products, their two buyer personas), build it as a Segment Contrast between two audiences and skip minting a
permanent named axis at all.

## The menu

| axis type | maps to this client decision | status | how to get it |
|---|---|---|---|
| **Political** | does political lean predict behavior here (real question, not default) | ready -- `Political Spectrum (2023)`, 16 anchors, r +0.893 | use as-is |
| **Income** | pricing tier, sponsorship level, premium-vs-value creative | ready -- `Income (2023)`, 27 anchors, r +0.839 | use as-is |
| **Gender** | creative/targeting split | ready -- `Female Contrast` | use as-is |
| **Occupation / persona (banking)** | which named persona this segment resembles | ready -- `SMB Owner`, `Hopscotch` (r +0.891/+0.869), `Attorney/Law` | use as-is; Tab-specific (`Tab Flow`/`ABL`/`Existing`/`Tabbank.com`) is that one client's own axes, not general-purpose |
| **Cultural/religious** | community targeting, local-market read | ready -- `Mormon Culture`, `LDS` | use as-is |
| **Urban vs. rural** | venue selection, expansion market, distribution | already named as a good choice in `heimdall-persona-clusters` (2026-09-06) but **no minted Plane-1 anchor exists yet** | build: signed anchor pair, e.g. `+downtown,+subway,+high rise -farmers market... ` vs `+rural route,+tractor,+county fair...` per `AUDIENCE_AXIS_REGISTER.md`'s affinity/content-topic register (do not mix registers in one anchor); or read Plane 2's POI state-share directly (`heimdall-legacy-scoring-planes` Plane 2) since urban/rural is closer to a physical-density question than a behavioral one |
| **Age / generational** | media mix, platform selection, creative tone | **no Plane-1 anchor. Live-Matrix pair exists**: `aud_genz_social` (tiktok shop, shein, depop, instagram shop) vs `aud_retirees_estate` (aarp, medicare, fidelity, retirement planning) -- filed under "Shopper Personas" in the `/v1/audiences` demo catalog, not labeled as an age axis anywhere | for a live-steering demo (`/steer`, `/generate`) these two IDs already work as an age contrast today -- use them and say so. For a client-deck X-axis, mint a Plane-1 anchor the same way (signed generational-affinity terms, demographic register per the axis register, NOT raw age-bucket terms which are attribute-only and won't fingerprint) |
| **Industry vertical** | which vertical's messaging fits this client's audience | **gap -- nothing exists at either layer** | build fresh: pick 2+ verticals relevant to the client (e.g. healthcare vs. finance vs. manufacturing decision-makers), seed each per the axis register's **firmographic** row (employer/workplace context, e.g. `epic systems`, `cerner`, `himss` for healthcare IT vs. `bloomberg terminal`, `sec filing`, `cfa institute` for finance) via `heimdall-create-audience`, verify with `/api/compose_check`, then either score as a Segment Contrast (client-specific) or, if this will recur across clients, mint a proper Plane-1 anchor |
| **Competitor vs. competitor** | which of two named brands this audience resembles | inherently per-client -- never a standing menu item | Segment Contrast: build both brands' audiences (`heimdall-create-audience`, affinity register -- brand names, not category terms), verify each with `/api/compose_check`, contrast per `heimdall-competitor-comparison` |
| **Product vs. product** | which of two named products/SKUs this audience prefers | inherently per-client | same as above, one audience per product line (in-market register if it is a purchase-intent question, affinity register if it is a loyalty question -- do not blend, see `AUDIENCE_AXIS_REGISTER.md`) |
| **Persona vs. persona** | which named buyer persona (e.g. IT Director vs. end user) this segment leans toward | inherently per-client, though the demo catalog's "Shopper Personas" category (`aud_small_business` vs. `aud_tech_early`, `aud_luxury_buyers` vs. `aud_bullion_stackers`, etc.) is a reusable STARTING PATTERN for how to build one | Segment Contrast between two hand-defined personas; reuse the demo catalog's pairs directly if the client's personas genuinely match one of the six existing pairs, otherwise build fresh |
| **Price sensitivity / value tier** | premium vs. discount positioning | ready, just not labeled as an axis -- `Shopping & Retail`'s `aud_specialty_retail` (whole foods, patagonia, rei, trader joes) vs. `aud_deal_hunters` (dollar general, five below, walmart, big lots) is explicitly commented "poles oppose on the price-valence axis" in `api_server.py` | use the live pair as-is for a steering demo; for a client-deck X-axis this overlaps heavily with Income -- prefer Income unless the client's question is specifically about retail price-tier rather than household income |
| **Life stage / life event** | timing a campaign to a transition (new parent, mover, retiree) | no standing axis; register exists (`AUDIENCE_AXIS_REGISTER.md`'s life-event row: change-of-state language, e.g. `just got engaged`, `new baby`, `moving`) | build per-client, Segment Contrast against Average Person rather than a fixed axis -- life events are inherently transient populations, not a stable second pole |

Think of more before reusing Political by default: **channel preference** (in-store-first vs. online-first,
useful for a retail/omnichannel client), **tech adoption curve** (`aud_tech_early` already exists as one side;
needs a genuine "late majority" foil rather than its current `aud_small_business` pairing, which is persona not
adoption-speed), **brand loyalty / tenure** (new customer vs. repeat buyer -- useful for retention-budget
decisions), **household composition** (family vs. single-person households -- useful for a CPG or insurance
client). None of these are built yet; treat them the same as Industry Vertical above -- real candidates, not
yet minted.

## Fixing a thin or wrong axis

`aud_tech_early`'s foil is `aud_small_business` -- that is a persona contrast wearing an adoption-curve label
(the category comment even says "Shopper Personas", not "Tech Adoption"). If a client actually needs an
adoption-curve axis, do not reuse this pair as-is: either relabel it honestly as a persona pair (what it
actually is) or build a real late-majority foil (e.g. `extended warranty`, `manufacturer coupon`, `big box
electronics`, `customer service phone number` -- affinity register, opposite of early-adopter behavior) via
`heimdall-improve-audience` / `heimdall-gads-formula-transform`. The same audit pattern that found "8 of 22
[custom audiences] filed on the wrong axis" in `AUDIENCE_AXIS_REGISTER.md` applies here: read what the seeds
actually say, not what the label claims, before reusing a pair as a stand-in for a different axis type.

## Verification

Whatever axis you pick, run the same gates `heimdall-client-deck` already requires for Political Spectrum:
r(Matrix h, plane score) on base rows should land in the 0.7-0.9 band the 2023 axes measured at (below ~0.7 the
formula did not compose as intended); r(x,y) 0.7-0.85 against the segment (>=0.95 means the two axes are one
thing -- switch to Segment Contrast); landmarks with their expected half, >=60% in place. A new axis that fails
these checks is not ready to ship regardless of how well-motivated the choice was.

## Platform blocks

If you are Claude Code, OpenClaw, Gemini or Codex: no platform-specific mechanics here beyond what
`heimdall-client-deck`, `heimdall-competitor-comparison`, `heimdall-legacy-scoring-planes` and
`heimdall-create-audience` already require on your toolset -- follow their platform blocks for the actual API
calls.

---
name: heimdall-term-disambiguation
description: Decide what a term MEANS before it becomes a seed, an anchor, or a chart dot in Heimdall — semantic collision probe, sense separation by subtraction, surface substitution (brand vs domain), and the exclude list. Use when a client's brand word has another sense (Ragnar, Vanguard, Heimdall, Apple, Delta), when an audience scores strangely, when a landscape row lands in the wrong half, or before seeding any single-word brand.
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset, UPDATE THIS SKILL with an `If you are [Platform]` block.

# Term disambiguation (what does this word mean to the corpus)

A seed is not a string, it is a population. `ragnar` carries the Norse sense (bare `ragnar` vs the Norse pole:
centred cosine 0.9484, `docs/RAGNAR_AUDIENCE_20260822.md` §4); `vanguard` carries the fund and the game;
`delta` the airline, the faucet and the variant. Seeding the bare word imports every sense's audience, and the
chart then reads as noise or, worse, as a confident wrong answer.

## 1. Probe before seeding — SEMANTIC, not lexical
`POST :8000/api/term_collisions {"terms": [...], "k": 8, "threshold": 0.55}` → per term the nearest published
anchors by embedding cosine and `live_collision` when the nearest clears the threshold. This is the semantic
neighbourhood, deliberately: the gateway's `/v1/admin/term_status` probe is head-word LEXICAL and for `ragnar`
finds `ragnar frisch` while missing `vikings` — the anchor that actually drags the Norse population in.
`embedded: false` means the term has no embedding — not known, never guessed. Run it on every single-word brand,
every surname, every 3–5 letter acronym, and every term that will carry weight ≥1 in a formula.

## 2. Separate the senses (in order of preference)
1. **Qualify the surface**: seed `ragnar relay`, `ragnar race`, `vanguard etf` instead of the bare word. Check
   volume — a qualified phrase with no Google volume is not a substitute, it is a hole (`no_volume` is a real
   answer; do not re-queue it).
2. **Subtract the other sense**: add the colliding anchors as negatives — `ragnar relay, -vikings*0.5,
   -norse mythology*0.5`. Weight the negative at half the positive unless the collision cosine is > 0.9, then 1×.
   Re-probe after: the collision should drop below threshold or the negative is landing on the wrong population.
3. **Split into two audiences** when both senses matter to the client (the race company AND the show fandom);
   never let one column carry both.

## 3. Surfaces are not senses
Same entity, different surface — `Deutsche Bank` ↔ `deutschebank.com`, `LINKEDIN` ↔ `linkedin.com` — is a
substitution, allowed, and named on the slide ("plotted as the domain"). A different SENSE is not a
substitution, it is an exclusion. Prefer the surface with volume and a Matrix row; entity/domain surfaces are
usually ADDENDUM rows, so score on the fingerprint plane (`heimdall-legacy-scoring-planes`).

## 4. Exclusions are part of the deliverable
Keep `exclude.json` per deck: zero-volume placeholders, meaning-changing substitutes, and rows whose sense
could not be separated — each with the one-line reason. A dot that cannot be defended by name does not ship.
When a landmark lands in the wrong half, disambiguation is the FIRST hypothesis to test, before the formula.

## 5. Verify the fix moved something
Re-score the audience and compare the movers, not the correlation: the top-20 by score should lose the other
sense's vocabulary. `POST /api/geomap {"audience_terms": [...]}` is the cheap second check — a Norse-contaminated
Ragnar maps to nothing recognisable; the race audience maps to Utah, Colorado, Washington.

## Platform blocks
### If you are Claude (Cowork / Claude Code)
Engine :8000 on the real Mac (Desktop Commander). `/api/term_collisions` needs embedded anchors in the live
cycle; a 503 `semantic_unavailable` means the cycle has none — say so rather than seeding blind.
### If you are Gemini / Codex
Same routes via `run_command`.

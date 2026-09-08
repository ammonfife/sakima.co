---
name: heimdall-insight-prompting
description: "The core prompting frame for every piece of client-facing prose generated from Heimdall numbers — Key Insight paragraphs, persona narratives, competitor call-outs, deck titles, BEN_DECISIONS_NEEDED entries. Adapts Google's Workspace-with-Gemini prompting guide (Persona/Task/Context/Format, instructions vs. constraints, iterative refinement, reusable \"Gems\") into a fixed template pre-loaded with Heimdall's own hard bans (no methodology words, no em-dash, no fabricated quotes, no cliche titles). Use before writing ANY sentence a client will read, before opening heimdall-client-deck's copy step, heimdall-persona-clusters' deck-copy step, or heimdall-competitor-comparison's movers writeup — or whenever a generation prompt for one of those needs building or fixing."
---

> [!IMPORTANT]
> **Cross-Platform Skill**: shared across Claude Code, OpenClaw, Gemini and Codex. Check the "Platform Blocks" at the end; if your platform is missing or a command fails on your toolset, UPDATE THIS SKILL with an `If you are [Platform]` block.

# Heimdall insight prompting (the PTCF frame, tuned to Heimdall's constraints)

This is the **core tuning** other Heimdall skills should build their generation prompts on, instead of
free-writing narrative copy each time. Companion skills that produce numbers to narrate: `heimdall-client-deck`
(step 8, the copy build), `heimdall-persona-clusters` (step 5, deck copy), `heimdall-competitor-comparison`
(step 5, movers writeup), `heimdall-2023-deck-recreation`. Adapted from Google's "Workspace with Gemini"
prompting guide (four components, instructions vs. constraints, iterative refinement, "Gems") — the general
technique is theirs; the constraint list baked in below is Heimdall's own, pulled from `README.md`, `CLAUDE.md`
and the "Upgrades learned" sections of `heimdall-client-deck` and `heimdall-persona-clusters`.

The problem this solves: every writer (human or agent) re-deriving "don't fabricate a quote, don't use an
em-dash, don't say Pearson" from memory produces drift — caught late, after a deck is already built (Ben:
"this is a lot of ai slop leaking into the deck," 109 em-dashes found on one pass). One fixed frame, applied at
generation time, catches it before the draft exists.

## The four components, mapped to Heimdall

1. **Persona** — who is speaking, to whom. Almost always: "You are a Genomic Digital analyst writing the
   [Key Insight / persona / competitor] section of a client deliverable for [client]." For an internal artifact
   (a `BEN_DECISIONS_NEEDED.md` entry, a `CHART_AUDIT.md` note) the persona is "internal, Ben-facing, no client
   filter" — say which one explicitly, because the constraint list below differs by persona (see §3).
2. **Task** — one imperative verb plus the exact artifact: "Write the Key Insight paragraph for the `<category>`
   chart," not "help me with this chart." Vague tasks produce vague drafts.
3. **Context** — the ONLY allowed source of facts is the actual scored output: named movers and their values from
   `deck_data.json` / `CHART_AUDIT.md`, the r value, the landmark read, the coverage %. This is Heimdall's version
   of the guide's `@[filename]` tagging — point at the real file/number, never let the model supply one. A number
   or a quote not traceable to a scored file does not go in the prompt's context and cannot appear in the output.
4. **Format** — sentence/paragraph count, "numbers embedded in prose, not a list," and the full ban list from §3
   restated as a constraint (models follow a constraint stated at point of use far more reliably than one implied
   by house style alone).

## Instructions vs. constraints

**Instructions** (what the draft MUST include): named movers with their actual numbers; the qualitative read
(which half, which landmark); negatives (3 per Key Insight page per `heimdall-client-deck`); the life-stage or
segment framing already established for the deck.

**Constraints** (Heimdall's fixed bans — copy these into every generation prompt verbatim, do not paraphrase):
- Never say "geospatial," "Pearson," "cosine," "embedding," or name the three bases (README rule #3). Public
  language is "audience voice intelligence" / "revealed-preference behavioral signal."
- "Heimdall" never appears in client-facing text — it is the internal codename only (README rule #4).
- Zero em-dashes. Not "minimal" — zero, anywhere in client copy.
- No fabricated first-person customer quotes. A data deck inventing quotation marks around invented speech reads
  as fabricated research — describe the persona in the third person instead, never as something someone said.
- No consulting-cliche single-word card titles (ACQUIRE / WARM / REVIVE / AVOID and the like).
- No "·" stat-separator tics or other AI-writing tells.
- "A client presentation, not an internal notebook" (Ben's standing correction) — no hedging, no meta-commentary
  about the methodology, no internal jargon leaking into client-facing sentences.

## Grounding: seed it, keep the mechanic internal, schedule the re-run

Before drafting from a scored row, check whether the underlying token or audience actually needed
grounding to get there. If it did, three rules, always together:

1. **Always seed/improve what's thin.** A skill that finds an ungrounded term or an under-covered
   audience does not draft around the gap -- it queues the term (`heimdall-full-topic-coverage`,
   `heimdall-audience-import`) or improves the audience (`heimdall-improve-audience`) before or
   alongside the copy pass. A silently-skipped gap is a wrong answer with confident phrasing.
2. **The seeding/queueing mechanic never appears in client-facing text.** "This term was queued for
   onboarding," "grounded at 62% coverage," any mention of `priority_source`, `tier`, or a re-run
   schedule -- all internal. It belongs in `CHART_AUDIT.md`, eval notes, or a `BEN_DECISIONS_NEEDED.md`
   entry, in the internal persona (see the Decision-memo Gem, §4), never in the Key-Insight/persona/
   competitor personas. Same boundary as the methodology-word ban in §3, one level up: the client
   never sees the machinery, seeding included.
3. **A queued term gets a scheduled re-run, not a one-off check.** Onboarding is asynchronous and
   serialised (`heimdall-full-topic-coverage` §3) -- queue it, then schedule the re-measure (a
   scheduled task, not a human watching a dashboard), and only draft the client-facing line once the
   re-run shows it grounded. "Queued" is not "measured."

**Writes to `master_keyword.db` go through its API, never a direct write.** Use
`POST /api/topic/coverage` (with `"tier": "interactive"` stated explicitly -- `heimdall-full-topic-coverage`)
or `POST /api/prefetch_onboard` (with the top-level `source` field set -- `heimdall-audience-import`;
an unset `source` writes zero rows to `master_keyword.priority_source` and the term silently falls to
machine-tier, per the measured 2026-09-06 incident). If a seeding need doesn't fit either route, that
is a real gap, not a license to `sqlite3.connect()` the table directly -- file it in
`BEN_DECISIONS_NEEDED.md` and use the nearest API in the meantime.

## Iterative refinement loop

Mirror the guide's "make it a conversation" pattern, in this fixed order:
1. **Draft** from the PTCF prompt (below).
2. **Qualitative audit** — run `heimdall-client-deck`'s five-decisions check (entity list, row existence, value
   trustworthiness, axes/band, what the movers say) against the drafted copy, not just the chart.
3. **Tone pass** — apply one of the guide's refinement chips as a literal follow-up instruction: "Formalize this,"
   "Make this more concise," "Elaborate on the [X] mover." Do this as a second turn, not folded into the first
   prompt — the guide's point that prompting is a conversation holds here too.
4. **Constraint re-check** — run the checklist in §5 as a literal pass over the final text before it ships, not
   as a mental note during drafting.

## Prompt template (copy, fill in brackets)

    Persona: You are a Genomic Digital analyst writing the [Key Insight paragraph / persona description /
    competitor call-out] for [client]'s audience deliverable.
    Task: Write [exact artifact, e.g. "the Key Insight paragraph for the Political Spectrum x Segment chart"].
    Context: Use only these scored facts — [paste named movers + values from deck_data.json/CHART_AUDIT.md, the
    r value, the landmark read]. Do not use any number, name, or quote not listed here.
    Format: [N] sentences, prose (no bullets), numbers embedded in the sentences, [state the tone: TAB-Bank
    Data-Science-Insights register / plain internal note].
    Constraints: Zero em-dashes. No fabricated first-person quotes. Never say geospatial, Pearson, cosine,
    embedding, or Heimdall. No single-word cliche card titles. [Add any deck-specific constraint here.]

## Gems (fixed reusable personas for repeat tasks)

Following the guide's "Gems" idea — a persona+format+constraints combination worth reusing rather than
rebuilding each time. Task and Context still change per call.

- **Key-Insight writer** — Persona: Genomic Digital analyst. Format: 3–5 sentences, movers-first, one qualitative
  read, no adjectives without a number behind them.
- **Persona-narrative writer** — Persona: same, describing a cluster. Format: third person, no invented speech,
  states cluster size and, when a demographic read matters, pulls it from `audience_profile` against
  the 91 `audience:gads:*` columns -- never defaults to a blanket "not scored: age/income/household"
  claim, which was true for one 2026-08-22 Ragnar pass and stayed wrong on the page for two weeks
  after the 2026-09-06 fix (CHART_AUDIT.md v4). Say "not measured" only when that call was
  actually skipped for this cluster (`heimdall-persona-clusters`).
- **Competitor-callout writer** — Persona: same, comparative register. Format: named movers on both sides of an
  axis, negatives included, no ranking language stronger than the r value supports.
- **Decision-memo writer** — Persona: internal, Ben-facing. Format: one line, category tag (Spend/Strategic/
  Infra/Findings/Handoff per `BEN_DECISIONS_NEEDED.md`'s existing scheme), no client-facing constraints apply
  (internal jargon is fine here; the em-dash and quote bans still apply — house style, not a client rule).

## Verification (§5, run before anything ships)

    grep -c '—' draft.txt                       # must be 0
    grep -iE 'geospatial|pearson|cosine|embedding|\bheimdall\b' draft.txt   # must be empty (case-sensitive on Heimdall)
    grep -n '"' draft.txt                        # any hit: confirm it is not an invented first-person quote

A chart image's own baked-in text (matplotlib/PIL labels) needs this same pass applied to its label strings and
a visual check at full size — grep only sees the extractable text layer, not rasterized labels
(`heimdall-persona-clusters`, upgrade learned 2026-09-06).

## Platform blocks
### If you are Claude (Cowork / Claude Code)
No engine call needed — this is a prompt-construction and text-QA skill. Run the grep pass with the Bash/shell
tool available on your platform against the drafted copy file before it goes into `content_static.json` /
`content_categories.json` or any client deliverable.
### If you are Gemini / Codex
Same frame. Where the platform offers native refinement chips (Formalize / Make more concise / Elaborate), use
those directly for the tone pass in step 3 instead of re-typing the instruction.
